#include <Servo.h>
#include <math.h>
#define kP -20

// Servos
Servo pitch;
Servo turret;
Servo shooter;

const float SWEEP_STEP_UNITS = 2.0;
const unsigned long SWEEP_PERIOD_MS = 12;

// Positional shooter (neutral is 90)
const int SHOOT_NEUTRAL = 90;
const unsigned long SHOOT_STEP_MS = 1000; // dwell per step: 0°, 180°, then 90°

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
  SHOOT_GO_0,
  SHOOT_GO_180,
  SHOOT_GO_90
};
ShootState shootState = SHOOT_IDLE;

String cmd = "";
int    cmdId = 0;
bool   cmdFound = false;
float  cmdDx = 0.0f;
float  cmdDz = 0.0f;       // <<< NEW: dz (meters) parsed from serial
int    cmdPitch = 0;       // still used by TRACK path
bool   cmdShoot = false;

// --- Moisture subsystem (non-blocking) ---
struct MoistureSensor {
  uint8_t pin;      // A0..A5
  const char* id;   // label in prints
  int dry;          // raw DRY (0%)
  int wet;          // raw WET (100%)
};

MoistureSensor MOIST_SENSORS[] = {
  {A0, "sensor_1", 450, 179},
  {A1, "sensor_2", 450, 179},
  {A2, "sensor_3", 450, 179},
  {A3, "sensor_4", 450, 179},
  {A4, "sensor_5", 450, 179},
};
const size_t MOIST_COUNT = sizeof(MOIST_SENSORS) / sizeof(MoistureSensor);

const unsigned long MOIST_PRINT_PERIOD_MS = 2000;
unsigned long _moist_next_ms = 0;

static float _moist_to_percent(int raw, int dry, int wet) {
  if (dry == wet) return 0.0f;
  float pct = (float)(dry - raw) / (float)(dry - wet);
  if (pct < 0.0f) pct = 0.0f;
  if (pct > 1.0f) pct = 1.0f;
  return pct;
}

static void maybePrintMoisture() {
  unsigned long now = millis();
  if (now < _moist_next_ms) return;
  _moist_next_ms = now + MOIST_PRINT_PERIOD_MS;

  for (size_t i = 0; i < MOIST_COUNT; ++i) {
    int raw = analogRead(MOIST_SENSORS[i].pin);
    float pct = _moist_to_percent(raw, MOIST_SENSORS[i].dry, MOIST_SENSORS[i].wet);
    Serial.print(F("cmd:MOISTURE;id:"));
    Serial.print(MOIST_SENSORS[i].id);
    Serial.print(F(";percent:"));
    Serial.print(pct, 1);
    Serial.print('\n');
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);

  pitch.attach(9, 1000, 2200);
  turret.attach(10);
  shooter.attach(8);

  pitch.write(149);                // your mechanical neutral
  shooter.write(SHOOT_NEUTRAL);
}

// Map helpers
int convertTurretAngle(int targetAngle){ return map(targetAngle, 0, 300, 0, 180); }
// NOTE: your previous code uses an offset of +149 when writing pitch.
// We keep convertPitchAngle for TRACK path. For WATER we now write absolute.
int convertPitchAngle(int targetAngle){ return targetAngle + 149; }

// --- Non-blocking shooter sequence: 0 -> 180 -> 90 ---
void shoot() {
  if (shootActive) return;
  shootActive  = true;
  shootState   = SHOOT_GO_0;
  shootStartMs = millis();
  shooter.write(0);
}

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
        shooter.write(SHOOT_NEUTRAL);
        shootState   = SHOOT_GO_90;
        shootStartMs = now;
      }
      break;

    case SHOOT_GO_90:
      if (now - shootStartMs >= SHOOT_STEP_MS) {
        shootState  = SHOOT_IDLE;
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
  serviceShooterTimer();
  maybePrintMoisture();

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
      alignedFrames = 0;
    } else {
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

    // Keep TRACK pitch behavior as-is (follows your earlier flow)
    pitch.write(convertPitchAngle(cmdPitch));

  } else if (cmd == "WATER") {
    // Parse fields (found, dx, dz, pitch kept but not used for WATER anymore)
    int idx_found = line.indexOf("found:");
    int idx_pitch = line.indexOf("pitch:");
    int idx_dx    = line.indexOf("dx:");
    int idx_dz    = line.indexOf("dz:");     // <<< NEW

    if (idx_found >= 0) {
      String s = line.substring(idx_found + 6, line.indexOf(';', idx_found));
      s.toLowerCase();
      cmdFound = (s == "true");
    }
    if (idx_pitch >= 0) {
      String s = line.substring(idx_pitch + 6, line.indexOf(';', idx_pitch));
      cmdPitch = s.toInt();
    }
    if (idx_dx >= 0) {
      String s = line.substring(idx_dx + 3, line.indexOf(';', idx_dx));
      cmdDx = s.toFloat();
    }
    if (idx_dz >= 0) {
      String s = line.substring(idx_dz + 3, line.indexOf(';', idx_dz));
      cmdDz = s.toFloat();  // meters from Python message
    }

    if (cmdFound) {
      // PID track while found (turret)
      if (!shootActive) {
        currTurretPos += cmdDx * kP;
        if (currTurretPos > 300) currTurretPos = 300;
        if (currTurretPos < 0)   currTurretPos = 0;
        turret.write(convertTurretAngle((int)currTurretPos));
      }

      // Alignment → shoot gate
      if (fabs(cmdDx) < ALIGN_THRESH_M && !shootActive) {
        alignedFrames++;
        if (alignedFrames >= STABLE_FRAMES_N) {
          shoot();
          alignedFrames = 0;
        }
      } else if (!shootActive) {
        alignedFrames = 0;
      }

    } else {
      // Not found → sweep
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

    // ===== NEW WATER PITCH CONTROL =====
    // pitch_deg = 90 - atan( 8cm / dz_cm ), using dz from Python (meters -> cm)
    float dz_cm = cmdDz * 100.0f;
    if (dz_cm < 0.5f) dz_cm = 0.5f;                 // avoid div-by-zero / tiny dz
    float pitch_rad = atanf(5.0f / dz_cm);          // atan in radians
    float pitch_deg = -(90.0f - (pitch_rad * 57.2958f)); // rad->deg

    // Constrain to servo's safe range (0..180). If your mech wants a smaller window, tighten here.
    int servoDeg = (int)roundf(pitch_deg);
    if (servoDeg < -22)   servoDeg = -22;
    if (servoDeg > 25) servoDeg = 25;

    // For WATER we drive the absolute servo angle directly:
    pitch.write(convertPitchAngle(servoDeg));
  }
}
