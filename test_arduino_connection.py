import serial
import time

ser = serial.Serial("/dev/tty.usbserial-A50285BI", 9600, timeout=1)

time.sleep(2) 
while True:
    ser.write(b"ON\n") 
    print("Sent: ON")
    time.sleep(2)

    ser.write(b"OFF\n")
    print("Sent: OFF")
    time.sleep(2)