#include <Servo.h>

Servo tester;   // create servo object
Servo test;
const int SERVO_PIN = 10;  // change to your signal pin

void setup() {
  tester.attach(SERVO_PIN);  // attach servo to pin
  test.attach(9);
}

void loop() {
  // Move to 0 degrees
  // tester.write(120);
  test.write(149-23);
  delay(500);
  test.write(149+20);
  // test.write(149);
  delay(500);

  // // Move to 90 degrees
  // tester.write(149-20);
  // delay(1000);

  // // Move to 180 degrees
  // tester.write(149+30);
  // delay(1000);
}
