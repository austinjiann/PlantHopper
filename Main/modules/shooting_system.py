"""
Shooting system for PlantHopper.
Coordinates sweep, search, and shoot operations.
"""
import time
import cv2
import numpy as np
from typing import Optional
from .arduino_controller import ArduinoController
from .apriltag_detector import AprilTagDetector, TagPose


class ShootingSystem:
    def __init__(self, arduino: ArduinoController, detector: AprilTagDetector,
                 sweep_duration: float = 2.0):
        """
        Initialize shooting system.
        
        Args:
            arduino: Arduino controller instance
            detector: AprilTag detector instance
            sweep_duration: How long to sweep before checking for tags (seconds)
        """
        self.arduino = arduino
        self.detector = detector
        self.sweep_duration = sweep_duration
        print("[ShootingSystem] Initialized")
    
    def sweep_and_search(self, target_tag_id: int, frame: np.ndarray) -> Optional[TagPose]:
        """
        Perform a sweep operation and search for target tag.
        
        Args:
            target_tag_id: AprilTag ID to search for
            frame: Current camera frame for detection
            
        Returns:
            TagPose if target found, None otherwise
        """
        # Send sweep command
        self.arduino.sweep()
        
        # Wait for sweep to complete
        time.sleep(self.sweep_duration)
        
        # Detect tags in current frame
        detections = self.detector.detect_tags(frame)
        
        # Check if target tag was found
        if target_tag_id in detections:
            pose = detections[target_tag_id]
            print(f"[ShootingSystem] Target tag {target_tag_id} found at "
                  f"position ({pose.tvec[0]:.3f}, {pose.tvec[1]:.3f}, {pose.tvec[2]:.3f})")
            
            # Send search command to Arduino for PID alignment
            dx_m = float(pose.tvec[0])
            pitch_deg = float(pose.pitch)
            self.arduino.search(target_tag_id, True, dx_m, pitch_deg, False)
            
            return pose
        else:
            print(f"[ShootingSystem] Target tag {target_tag_id} not found")
            # Send search command indicating tag not found
            self.arduino.search(target_tag_id, False, 0.0, 0, False)
            return None
    
    def shoot_at_tag(self, pose: TagPose) -> bool:
        """
        Shoot at a detected AprilTag.
        
        Args:
            pose: TagPose object with target information
            
        Returns:
            True if shoot command sent successfully
        """
        dx_m = float(pose.tvec[0])  # Horizontal offset
        pitch_deg = float(pose.pitch)  # Pitch angle
        
        print(f"[ShootingSystem] Shooting at tag {pose.tag_id}: "
              f"dx={dx_m:.3f}m, pitch={pitch_deg:.1f}°")
        
        return self.arduino.shoot(dx_m, pitch_deg)
    
    def sweep_search_shoot_cycle(self, target_tag_id: int, cap: cv2.VideoCapture,
                                  max_cycles: int = 3) -> bool:
        """
        Execute complete sweep-search-shoot cycle.
        Performs up to max_cycles sweeps, shooting if target is found.
        
        Args:
            target_tag_id: AprilTag ID to search for
            cap: OpenCV video capture object for getting frames
            max_cycles: Maximum number of sweep cycles to attempt
            
        Returns:
            True if target was found and shot, False otherwise
        """
        print(f"[ShootingSystem] Starting sweep-search-shoot cycle for tag {target_tag_id}")
        
        for cycle in range(1, max_cycles + 1):
            print(f"[ShootingSystem] Cycle {cycle}/{max_cycles}")
            
            # Grab current frame
            ok, frame = cap.read()
            if not ok:
                print("[ShootingSystem] Failed to grab frame")
                continue
            
            # Sweep and search for target
            pose = self.sweep_and_search(target_tag_id, frame)
            
            # If found, shoot and return success
            if pose is not None:
                success = self.shoot_at_tag(pose)
                if success:
                    print(f"[ShootingSystem] Successfully shot at tag {target_tag_id}")
                    return True
                else:
                    print(f"[ShootingSystem] Failed to send shoot command")
            
            # Small delay before next cycle
            time.sleep(0.5)
        
        print(f"[ShootingSystem] Target tag {target_tag_id} not found after {max_cycles} cycles")
        return False
    
    def continuous_tracking_shoot(self, target_tag_id: int, cap: cv2.VideoCapture,
                                   duration: float = 10.0) -> bool:
        """
        Continuously track and shoot at target tag for specified duration.
        Useful for moving targets or when precise timing is needed.
        
        Args:
            target_tag_id: AprilTag ID to track
            cap: OpenCV video capture object
            duration: How long to track for (seconds)
            
        Returns:
            True if at least one shot was made
        """
        print(f"[ShootingSystem] Continuous tracking for {duration}s")
        
        start_time = time.time()
        shot_made = False
        
        while (time.time() - start_time) < duration:
            ok, frame = cap.read()
            if not ok:
                continue
            
            detections = self.detector.detect_tags(frame)
            
            if target_tag_id in detections:
                pose = detections[target_tag_id]
                self.shoot_at_tag(pose)
                shot_made = True
                time.sleep(0.5)  # Rate limit shooting
        
        return shot_made