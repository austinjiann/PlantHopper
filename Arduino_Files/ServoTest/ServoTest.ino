#include <Servo.h>

// ---- Pins ----
#define TURRET_PIN 10

// ---- Logical range (we control in 0..120), mapped to servo 0..180 ----
#define LOGICAL_MIN     0
#define LOGICAL_MAX   120
#define SERVO_MIN_DEG   0
#define SERVO_MAX_DEG 180

// ---- Sweep tuning ----
const unsigned long SWEEP_PERIOD_MS = 12;   // time between steps
const float         SWEEP_STEP_UNITS = 1.0; // logical units per step (~24°/s overall)

// ---- State ----
Servo turret;
float currPos = 60.0f;          // start at midpoint of 0..120
int   sweepDir = +1;
unsigned long lastStepMs = 0;
bool  demoDone = false;         // run the 0→120 demo once, then sweep forever

// ---- Helpers ----
int clampInt(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

// Map logical 0..120 → servo 0..180 (with clamping for safety)
int convertTurretAngle(int logicalAngle) {
  logicalAngle = clampInt(logicalAngle, LOGICAL_MIN, LOGICAL_MAX);
  return map(logicalAngle, LOGICAL_MIN, LOGICAL_MAX, SERVO_MIN_DEG, SERVO_MAX_DEG);
}

// Set turret in *logical* units; we handle mapping & caps internally
void setTurretLogical(int logicalAngle) {
  int servoDeg = convertTurretAngle(logicalAngle);
  turret.write(servoDeg);
}

void setup() {
  // If your servo needs a specific pulse range, use: turret.attach(TURRET_PIN, 1000, 2000);
  turret.attach(TURRET_PIN);
  setTurretLogical(60); // midpoint
}

void loop() {
  // --- One-time demo: go to 0, wait, then 120, wait ---
  if (!demoDone) {
    setTurretLogical(0);
    delay(2000);
    setTurretLogical(120);
    delay(2000);
    demoDone = true;
  }

  // --- Continuous sweep between 0..120 logical (mapped to 0..180 servo) ---
  unsigned long now = millis();
  if (now - lastStepMs >= SWEEP_PERIOD_MS) {
    lastStepMs = now;

    currPos += sweepDir * SWEEP_STEP_UNITS;
    if (currPos >= LOGICAL_MAX) { currPos = LOGICAL_MAX; sweepDir = -1; }
    if (currPos <= LOGICAL_MIN) { currPos = LOGICAL_MIN; sweepDir = +1; }

    setTurretLogical((int)currPos);
  }
}
