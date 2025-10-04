#include <Servo.h>

// Servo myServo;
Servo myServo2;


void setup() {
  // myServo.attach(10); 
  myServo2.attach(10, 1000, 2200);
   // adjust to your servo’s safe range

}

void loop() {

  myServo2.write(180);

  // myServo2.write(140);


  // myServo.write(0);

  delay(5000);


  // myServo.write(165);
  // myServo2.write(165);


  // delay(2000);

  // myServo.write(100);

  // delay(2000);
}
