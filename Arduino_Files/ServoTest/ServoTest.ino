#include <Servo.h>

Servo myServo;

void setup() {
  myServo.attach(9); 
}

void loop() {

  myServo.write(0);

  delay(2000);

  // myServo.write(300);

  // delay(2000);
}
