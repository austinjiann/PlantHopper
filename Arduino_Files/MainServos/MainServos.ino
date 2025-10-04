#include <Servo.h>

const int BASE_PIN   = 6;   // positional
const int PITCH_PIN  = 7;   // positional
const int SHOOT_PIN  = 8;   // continuous

// prevent drifting
const int SHOOTER_STOP_US  = 1500;   // neutral pulse
const int SHOOTER_RANGE_US = 500;    // +/- 500 => 1000..2000 µs

Servo servoBase, servoPitch, servoShooter;

void setServosRaw(int base_deg, int pitch_deg, float shoot_pct) {

  servoBase.write((int)base_deg);
  servoPitch.write((int)pitch_deg);

  // Continuous: linear map -100..100 -> 1000..2000 µs (no deadband)
  int us = SHOOTER_STOP_US + (int)(shoot_pct * (SHOOTER_RANGE_US / 100.0f));
  servoShooter.writeMicroseconds(us);
}

void parseLineAndUpdate(const String& line) {
  // Format: "base:<deg>;pitch:<deg>;shoot:<-100..100|ON|OFF>"
  int idx_base  = line.indexOf("base:");
  int idx_pitch = line.indexOf("pitch:");
  int idx_shoot = line.indexOf("shoot:");

  static float base_deg = 90, pitch_deg = 90, shoot_pct = 0;

  if (idx_base >= 0) {
    int end = line.indexOf(';', idx_base);
    String s = (end >= 0) ? line.substring(idx_base + 5, end) : line.substring(idx_base + 5);
    s.trim();
    base_deg = s.toFloat();
  }
  if (idx_pitch >= 0) {
    int end = line.indexOf(';', idx_pitch);
    String s = (end >= 0) ? line.substring(idx_pitch + 6, end) : line.substring(idx_pitch + 6);
    s.trim();
    pitch_deg = s.toFloat();
  }
  if (idx_shoot >= 0) {
    int end = line.indexOf(';', idx_shoot);
    String s = (end >= 0) ? line.substring(idx_shoot + 6, end) : line.substring(idx_shoot + 6);
    s.trim();
    String sl = s; sl.toLowerCase();
    if (sl == "on")      shoot_pct = 100.0;
    else if (sl == "off") shoot_pct = 0.0;
    else                 shoot_pct = s.toFloat();  // expect -100..100
  }

  setServosRaw((int)base_deg, (int)pitch_deg, shoot_pct);

  Serial.print("OK base=");  Serial.print((int)base_deg);
  Serial.print(" pitch=");   Serial.print((int)pitch_deg);
  Serial.print(" shoot%=");  Serial.println((int)shoot_pct);
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(5);

  servoBase.attach(BASE_PIN);
  servoPitch.attach(PITCH_PIN);
  servoShooter.attach(SHOOT_PIN);

  // Start at safe defaults
  setServosRaw(90, 90, 0);
  Serial.println("Ready. Use: base:90;pitch:30;shoot:60   or   shoot:ON/OFF");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) parseLineAndUpdate(line);
  }
}
