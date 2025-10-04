import serial
import time

ser = serial.Serial("/dev/tty.usbserial-A50285BI", 9600, timeout=1)

time.sleep(2) 
while True:
    ser.write("cmd:search;id:1;found:true;dx:0;pitch:0;shoot:false\n".encode()) 
    print("Sent")
    time.sleep(2)

    ser.write("cmd:search;id:1;found:true;dx:90;pitch:30;shoot:false\n".encode())
    print("Sent: OFF")
    time.sleep(2)
