"""
Arduino controller for PlantHopper system.
Handles serial communication for sweep and shoot commands.
"""
import serial
import time
from typing import Optional


class ArduinoController:
    def __init__(self, port: str = "/dev/tty.usbserial-A50285BI", baudrate: int = 115200):
        """
        Initialize Arduino serial connection.
        
        Args:
            port: Serial port path
            baudrate: Communication speed
        """
        self.ser = serial.Serial(port, baudrate, timeout=1, write_timeout=1)
        time.sleep(3)  # Wait for Arduino to initialize
        print(f"[Arduino] Connected to {port}")
    
    def send_command(self, command: str) -> bool:
        """
        Send a command string to Arduino.
        
        Args:
            command: Command string to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ser.write(command.encode())
            print(f"[Arduino] Sent: {command.strip()}")
            return True
        except Exception as e:
            print(f"[Arduino] Error sending command: {e}")
            return False
    
    def sweep(self) -> bool:
        """
        Send sweep command to Arduino.
        
        Returns:
            True if successful
        """
        command = "cmd:SWEEP\n"
        return self.send_command(command)
    
    def shoot(self, dx_m: float, pitch_deg: float) -> bool:
        """
        Send shoot command with targeting parameters.
        
        Args:
            dx_m: Horizontal offset in meters
            pitch_deg: Pitch angle in degrees
            
        Returns:
            True if successful
        """
        command = f"cmd:SHOOT;dx:{dx_m:.3f};pitch:{int(round(pitch_deg))}\n"
        return self.send_command(command)
    
    def search(self, tag_id: int, found: bool, dx_m: float, pitch_deg: float, shoot: bool) -> bool:
        """
        Send search command with tag detection info.
        
        Args:
            tag_id: AprilTag ID being searched for
            found: Whether tag was detected
            dx_m: Horizontal offset in meters
            pitch_deg: Pitch angle in degrees
            shoot: Whether to trigger shooting
            
        Returns:
            True if successful
        """
        command = (
            f"cmd:SEARCH;"
            f"id:{tag_id};"
            f"found:{str(found).lower()};"
            f"dx:{dx_m:.3f};"
            f"pitch:{int(round(pitch_deg))};"
            f"shoot:{str(shoot).lower()}\n"
        )
        return self.send_command(command)
    
    def close(self):
        """Close the serial connection."""
        if self.ser.is_open:
            self.ser.close()
            print("[Arduino] Connection closed")


    