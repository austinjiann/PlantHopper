#include <Servo.h>

Servo tester;   // create servo object
const int SERVO_PIN = 9;  // change to your signal pin

void setup() {
  tester.attach(SERVO_PIN, 1000, 2200);  // attach servo to pin
}

void loop() {
  // Move to 0 degrees
  tester.write(149);
  delay(1000);

  // Move to 90 degrees
  tester.write(149-20);
  delay(1000);

  // Move to 180 degrees
  tester.write(149+30);
  delay(1000);
}
