#include <Servo.h>

// Servo myServo;
Servo pitch;
Servo turret;
bool shoot = false;
double currTurretPos = 0;


void setup() {
  pitch.attach(9, 1000, 2200); 
  turret.attach(10);
   // adjust to your servo’s safe range

}

int convertTurretAngle(int targetAngle){
  return map(targetAngle, 0, 300, 0, 180);
}

// it's relative to straight being (0)
int convertPitchAngle(int targetAngle){
  return targetAngle - 149;
}

void loop() {
  if (!Serial.available()) return;

  //if cmd is "search": "cmd:word;id:num;found:bool;dx:num;pitch:deg;shoot:bool"
  String line = Serial.readStringUntil('\n');
  line.trim();   // remove CR/LF or spaces

  int idx_cmd   = line.indexOf("cmd:");
  int idx_id    = line.indexOf("id:");
  int idx_found = line.indexOf("found:");
  int idx_dx    = line.indexOf("dx:");
  int idx_pitch = line.indexOf("pitch:");
  int idx_shoot = line.indexOf("shoot:");

  if (idx_cmd >= 0) {
    String s = line.substring(idx_cmd + 4, line.indexOf(';', idx_cmd));
    cmd = s;   // String type
  }

  if (idx_id >= 0) {
    String s = line.substring(idx_id + 3, line.indexOf(';', idx_id));
    cmdId = s.toInt();   // integer
  }

  if (idx_found >= 0) {
    String s = line.substring(idx_found + 6, line.indexOf(';', idx_found));
    s.toLowerCase();
    cmdFound = (s == "true");  // boolean
  }

  if (idx_dx >= 0) {
    String s = line.substring(idx_dx + 3, line.indexOf(';', idx_dx));
    cmdDx = s.toFloat();   // double / float
  }

  if (idx_pitch >= 0) {
    String s = line.substring(idx_pitch + 6, line.indexOf(';', idx_pitch));
    cmdPitch = s.toInt();   // int
  }

  if (idx_shoot >= 0) {
    String s = line.substring(idx_shoot + 6, line.indexOf(';', idx_shoot));
    s.toLowerCase();
    cmdShoot = (s == "true");  // boolean
  }

  if(idx_found){
    //run PID to align
    currTurretPos += dx
    turret.write(convertTurretAngle(currTurretPos));
    pitch.write(convertPitchAngle(cmdPitch));
  }

  // myServo2.write(140);


  // myServo.write(0);

  delay(200);


  // myServo.write(165);
  // myServo2.write(165);


  // delay(2000);

  // myServo.write(100);

  // delay(2000);
}
