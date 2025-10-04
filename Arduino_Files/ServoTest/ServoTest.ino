#include <Servo.h>

// Servo myServo;
Servo myServo2;


void setup() {
  // myServo.attach(10); 
  myServo2.attach(10);
   // adjust to your servo’s safe range

}

void loop() {

  int desiredAngle = 0;  // Example target (0–300 scale)

  // Map from 0–300 → 0–180
  int servoAngle = map(desiredAngle, 0, 300, 0, 180);

  myServo2.write(servoAngle);

  // myServo2.write(140);


  // myServo.write(0);

  delay(5000);


  // myServo.write(165);
  // myServo2.write(165);


  // delay(2000);

  // myServo.write(100);

  // delay(2000);
}
