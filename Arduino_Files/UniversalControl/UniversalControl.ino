#include <Servo.h>
#include <math.h>
#define kP -20

// Servos
Servo pitch;
Servo turret;
Servo shooter;

const float SWEEP_STEP_UNITS = 0.8;
const unsigned long SWEEP_PERIOD_MS = 20;

// Positional shooter (neutral is 90)
const int SHOOT_NEUTRAL = 90;
const unsigned long SHOOT_STEP_MS = 1500; // dwell per step: 0°, 180°, then 90°

// Alignment gating for WATER
const float ALIGN_THRESH_M   = 0.020f; // |dx| < 2 cm
const int   STABLE_FRAMES_N  = 8;      // consecutive frames aligned before shooting
int alignedFrames = 0;

double currTurretPos = 150.0;          // logical 0..300 mapped to 0..180 servo
int    sweepDir = +1;
unsigned long lastStepMs = 0;

// Shooter state (non-blocking)
bool shootActive = false;
unsigned long shootStartMs = 0;

enum ShootState : uint8_t {
  SHOOT_IDLE = 0,
  SHOOT_GO_0,     // move to 0°
  SHOOT_GO_180,   // then to 180°
  SHOOT_GO_90     // finally to 90° (neutral)
};
ShootState shootState = SHOOT_IDLE;

String cmd = "";
int    cmdId = 0;
bool   cmdFound = false;
float  cmdDx = 0.0f;
int    cmdPitch = 0;
bool   cmdShoot = false;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);

  pitch.attach(9, 1000, 2200);
  turret.attach(10);
  shooter.attach(8);

  pitch.write(149);
  shooter.write(SHOOT_NEUTRAL); // start stopped
}

// Map helpers
int convertTurretAngle(int targetAngle){ return map(targetAngle, 0, 300, 0, 180); }
int convertPitchAngle(int targetAngle){ return targetAngle + 149; }

// --- Non-blocking shooter sequence: 0 -> 180 -> 90 ---
void shoot() {
  if (shootActive) return;            // already running; ignore
  shootActive  = true;
  shootState   = SHOOT_GO_0;
  shootStartMs = millis();
  shooter.write(0);                   // first position
}

// Advances the shooter sequence without blocking.
void serviceShooterTimer() {
  if (!shootActive) return;

  unsigned long now = millis();
  switch (shootState) {
    case SHOOT_GO_0:
      if (now - shootStartMs >= SHOOT_STEP_MS) {
        shooter.write(180);
        shootState   = SHOOT_GO_180;
        shootStartMs = now;
      }
      break;

    case SHOOT_GO_180:
      if (now - shootStartMs >= SHOOT_STEP_MS) {
        shooter.write(SHOOT_NEUTRAL);       // 90°
        shootState   = SHOOT_GO_90;
        shootStartMs = now;
      }
      break;

    case SHOOT_GO_90:
      if (now - shootStartMs >= SHOOT_STEP_MS) {
        shootState  = SHOOT_IDLE;           // done
        shootActive = false;
      }
      break;

    default:
      shooter.write(SHOOT_NEUTRAL);
      shootState  = SHOOT_IDLE;
      shootActive = false;
      break;
  }
}

void loop() {
  // Service shooter timer EVERY loop so it remains non-blocking
  serviceShooterTimer();

  // Only act when a serial line arrives
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();

  // Parse command word
  int idx_cmd = line.indexOf("cmd:");
  if (idx_cmd >= 0) {
    String s = line.substring(idx_cmd + 4, line.indexOf(';', idx_cmd));
    s.toUpperCase();
    cmd = s;
  }

  if (cmd == "TRACK") {
    // Parse fields we care about
    int idx_found = line.indexOf("found:");
    int idx_dx    = line.indexOf("dx:");
    int idx_pitch = line.indexOf("pitch:");

    if (idx_found >= 0) {
      String s = line.substring(idx_found + 6, line.indexOf(';', idx_found));
      s.toLowerCase();
      cmdFound = (s == "true");
    }
    if (idx_dx >= 0) {
      String s = line.substring(idx_dx + 3, line.indexOf(';', idx_dx));
      cmdDx = s.toFloat();
    }
    if (idx_pitch >= 0) {
      String s = line.substring(idx_pitch + 6, line.indexOf(';', idx_pitch));
      cmdPitch = s.toInt();
    }

    if (cmdFound) {
      currTurretPos += cmdDx * kP;
      if (currTurretPos > 300) currTurretPos = 300;
      if (currTurretPos < 0)   currTurretPos = 0;
      turret.write(convertTurretAngle((int)currTurretPos));
      alignedFrames = 0; // TRACK: no shooting logic; just reset
    } else {
      unsigned long now = millis();
      if (now - lastStepMs >= SWEEP_PERIOD_MS) {
        lastStepMs = now;

        currTurretPos += sweepDir * SWEEP_STEP_UNITS;
        if (currTurretPos >= 300) { currTurretPos = 300; sweepDir = -1; }
        if (currTurretPos <=   0) { currTurretPos =   0; sweepDir = +1; }

        turret.write(convertTurretAngle((int)currTurretPos));
      }
      alignedFrames = 0; // TRACK: not aligning; ensure reset
    }
    pitch.write(convertPitchAngle(cmdPitch));  // keep your search/track pitch

    // Ensure shooter stays off in TRACK
    // (If you want to hard-cancel any ongoing sequence in TRACK, uncomment:)
    // if (shootActive) { shooter.write(SHOOT_NEUTRAL); shootActive = false; shootState = SHOOT_IDLE; }
  }

  else if (cmd == "WATER") {
    // Parse fields
    int idx_found = line.indexOf("found:");
    int pitch_id  = line.indexOf("pitch:");
    int idx_dx    = line.indexOf("dx:");

    if (idx_found >= 0) {
      String s = line.substring(idx_found + 6, line.indexOf(';', idx_found));
      s.toLowerCase();
      cmdFound = (s == "true");
    }
    if (pitch_id >= 0) {
      String s = line.substring(pitch_id + 6, line.indexOf(';', pitch_id));
      cmdPitch = s.toInt();
    }
    if (idx_dx >= 0) {
      String s = line.substring(idx_dx + 3, line.indexOf(';', idx_dx));
      cmdDx = s.toFloat();
    }

    if (cmdFound) {
      // PID track while found
      if (!shootActive) { // optional: avoid steering during the short shot sequence
        currTurretPos += cmdDx * kP;
        if (currTurretPos > 300) currTurretPos = 300;
        if (currTurretPos < 0)   currTurretPos = 0;
        turret.write(convertTurretAngle((int)currTurretPos));
      }

      // Fire once after stable alignment
      if (fabs(cmdDx) < ALIGN_THRESH_M && !shootActive) {
        alignedFrames++;
        if (alignedFrames >= STABLE_FRAMES_N) {
          shoot();                 // run 0° -> 180° -> 90° (non-blocking)
          alignedFrames = 0;       // reset counter after trigger
        }
      } else if (!shootActive) {
        alignedFrames = 0;         // only reset if not in the middle of a sequence
      }
    } else {
      // Not found → sweep like TRACK
      unsigned long now = millis();
      if (now - lastStepMs >= SWEEP_PERIOD_MS) {
        lastStepMs = now;

        currTurretPos += sweepDir * SWEEP_STEP_UNITS;
        if (currTurretPos >= 300) { currTurretPos = 300; sweepDir = -1; }
        if (currTurretPos <=   0) { currTurretPos =   0; sweepDir = +1; }

        turret.write(convertTurretAngle((int)currTurretPos));
      }
      alignedFrames = 0;
    }

    // WATER pitch behavior (your existing offset/scale)
    pitch.write(convertPitchAngle((cmdPitch - 15) * 1.5));
  }
}
