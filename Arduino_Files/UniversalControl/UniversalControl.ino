#include <Servo.h>
#include <math.h>
#define kP -20

// Servos
Servo pitch;
Servo turret;
Servo shooter;

const float SWEEP_STEP_UNITS = 1.2;
const unsigned long SWEEP_PERIOD_MS = 20;

const int SHOOT_NEUTRAL = 90;        // stop for continuous servo (90 ~ 1500us)
const int SHOOT_ON      = 180;       // run (flip to 0 if direction is wrong)
const unsigned long SHOOT_BURST_MS = 5000;  // match your old delay(5000)

double currTurretPos = 150.0;
int    sweepDir = +1;
unsigned long lastStepMs = 0;

bool   shootActive = false;          // shooter state machine
unsigned long shootStartMs = 0;

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

void serviceShooterTimer() {
  if (!shootActive) return;
  unsigned long now = millis();
  if (now - shootStartMs >= SHOOT_BURST_MS) {
    shooter.write(SHOOT_NEUTRAL);    // auto-stop when burst time elapses
    shootActive = false;
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

  if (cmd == "SEARCH") {
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
      pitch.write(convertPitchAngle(cmdPitch));
    } else {
      unsigned long now = millis();
      if (now - lastStepMs >= SWEEP_PERIOD_MS) {
        lastStepMs = now;

        currTurretPos += sweepDir * SWEEP_STEP_UNITS;
        if (currTurretPos >= 300) { currTurretPos = 300; sweepDir = -1; }
        if (currTurretPos <=   0) { currTurretPos =   0; sweepDir = +1; }

        turret.write(convertTurretAngle((int)currTurretPos));
      }
      pitch.write(convertPitchAngle(cmdPitch));  // keep your search pitch
    }
  }

  else if (cmd == "SHOOT") {
    int pitch_id = line.indexOf("pitch:");
    int idx_dx   = line.indexOf("dx:");
    if (pitch_id >= 0) {
      String s = line.substring(pitch_id + 6, line.indexOf(';', pitch_id)); // +6
      cmdPitch = s.toInt();
    }
    if (idx_dx >= 0) {
      String s = line.substring(idx_dx + 3, line.indexOf(';', idx_dx));
      cmdDx = s.toFloat();
    }

    if (fabs(cmdDx) < 0.02f) {
      if (!shootActive) {
        shooter.write(SHOOT_ON);    
        shootStartMs = millis();
        shootActive  = true;
      }
    } else {
      if (shootActive) {
        shooter.write(SHOOT_NEUTRAL);
        shootActive = false;
      }
      currTurretPos += cmdDx * kP;
      if (currTurretPos > 300) currTurretPos = 300;
      if (currTurretPos < 0)   currTurretPos = 0;
      turret.write(convertTurretAngle((int)currTurretPos));
    }

    pitch.write(convertPitchAngle(cmdPitch + 20));
  }
}
