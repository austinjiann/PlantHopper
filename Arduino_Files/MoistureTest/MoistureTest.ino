// Five soil moisture sensors on A0..A4, printed as CSV every 2s.
// Uses per-sensor calibration: "dry" (0%) and "wet" (100%) raw ADC values.

struct Sensor {
  uint8_t pin;     // A0..A5
  String  id;      // label for prints
  int     dry;     // raw value when probe is DRY   (0% moisture)
  int     wet;     // raw value when probe is WET   (100% moisture)
};

Sensor sensors[] = {
  {A0, "sensor_1", 820, 300},
  {A1, "sensor_2", 820, 300},
  {A2, "sensor_3", 820, 300},
  {A3, "sensor_4", 820, 300},
  {A4, "sensor_5", 820, 300},
};
const int NUM_SENSORS = sizeof(sensors) / sizeof(sensors[0]);

// Sampling period (non-blocking)
const unsigned long SAMPLE_PERIOD_MS = 2000;
unsigned long lastSampleMs = 0;

//179 is lowest

// --- helpers ---
int readAveraged(uint8_t pin, uint8_t n = 5) {
  long acc = 0;
  for (uint8_t i = 0; i < n; ++i) {
    acc += analogRead(pin);
  }
  return (int)(acc / n);
}

// Map raw reading to 0..100% using this sensor's calibration
int rawToPercent(int raw, int dry, int wet) {
  // Constrain and map; many capacitive sensors read HIGH when dry, LOW when wet
  raw = constrain(raw, 0, 1023);
  int pct = map(raw, dry, wet, 0, 100);    // dry -> 0%, wet -> 100%
  return constrain(pct, 0, 100);
}

void setup() {
  Serial.begin(115200);
  // Optional: pinMode inputs (analog pins default to input)
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(sensors[i].pin, INPUT);
  }
  // CSV header
  Serial.println(F("id,raw,percent"));
}

void loop() {
  unsigned long now = millis();
  if (now - lastSampleMs >= SAMPLE_PERIOD_MS) {
    lastSampleMs = now;

    for (int i = 0; i < NUM_SENSORS; i++) {
      int raw = readAveraged(sensors[i].pin, 5);
      int pct = rawToPercent(raw, sensors[i].dry, sensors[i].wet);

      Serial.print(sensors[i].id);
      Serial.print(",");
      Serial.print(raw);
      Serial.print(",");
      Serial.print(sensors[i].pin);
      Serial.print(",");
      Serial.println(pct);
    }
  }

  // Do other non-blocking work here...
}
