"""
AprilTag detection module for PlantHopper system.
Provides thread-safe tag detection and pose estimation.
"""
import cv2
import numpy as np
import threading
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class TagPose:
    """Container for AprilTag pose information."""
    tag_id: int
    tvec: np.ndarray  # Translation vector [x, y, z] in meters
    rvec: np.ndarray  # Rotation vector
    roll: float  # Rotation around X-axis (degrees)
    pitch: float  # Rotation around Y-axis (degrees)
    yaw: float  # Rotation around Z-axis (degrees)
    distance: float  # Distance from camera (meters)


class AprilTagDetector:
    def __init__(self, calib_path: str, tag_size: float = 0.072, 
                 dict_name: str = "DICT_APRILTAG_36h11"):
        """
        Initialize AprilTag detector with camera calibration.
        
        Args:
            calib_path: Path to camera calibration YAML file
            tag_size: Physical size of tags in meters
            dict_name: AprilTag dictionary name
        """
        self.tag_size = tag_size
        self.camera_matrix, self.dist_coeffs = self._load_calibration(calib_path)
        
        # Setup detector
        dictionary_id = getattr(cv2.aruco, dict_name)
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.params)
        
        # Thread safety
        self.lock = threading.Lock()
        self.latest_detections: Dict[int, TagPose] = {}
        
        print(f"[Detector] Initialized with {dict_name}")
    
    def _load_calibration(self, calib_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Load camera calibration from file."""
        fs = cv2.FileStorage(calib_path, cv2.FILE_STORAGE_READ)
        if not fs.isOpened():
            raise FileNotFoundError(f"Could not open calibration file: {calib_path}")
        
        camera_matrix = fs.getNode("camera_matrix").mat()
        dist_coeffs = fs.getNode("dist_coeffs").mat()
        fs.release()
        
        if camera_matrix is None or dist_coeffs is None:
            raise ValueError("Calibration file missing 'camera_matrix' or 'dist_coeffs'.")
        
        return camera_matrix, dist_coeffs
    
    def _rvec_to_euler_xyz(self, rvec: np.ndarray) -> Tuple[float, float, float]:
        """Convert rotation vector to Euler angles (roll, pitch, yaw)."""
        R, _ = cv2.Rodrigues(rvec)
        sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
        singular = sy < 1e-6
        
        if not singular:
            roll = np.arctan2(R[2,1], R[2,2])
            pitch = np.arctan2(-R[2,0], sy)
            yaw = np.arctan2(R[1,0], R[0,0])
        else:
            roll = np.arctan2(-R[1,2], R[1,1])
            pitch = np.arctan2(-R[2,0], sy)
            yaw = 0.0
        
        return roll, pitch, yaw
    
    def detect_tags(self, frame: np.ndarray) -> Dict[int, TagPose]:
        """
        Detect AprilTags in frame and estimate poses.
        
        Args:
            frame: Input image (BGR format)
            
        Returns:
            Dictionary mapping tag IDs to TagPose objects
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        detections = {}
        
        if ids is not None and len(ids) > 0:
            # Define 3D object points for the tag
            obj_points = np.array([
                [-self.tag_size/2, self.tag_size/2, 0],
                [self.tag_size/2, self.tag_size/2, 0],
                [self.tag_size/2, -self.tag_size/2, 0],
                [-self.tag_size/2, -self.tag_size/2, 0]
            ], dtype=np.float32)
            
            for i, corner in enumerate(corners):
                success, rvec, tvec = cv2.solvePnP(
                    obj_points, corner, self.camera_matrix, self.dist_coeffs,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE
                )
                
                if success:
                    tag_id = int(ids[i])
                    rvec = rvec.reshape(-1)
                    tvec = tvec.reshape(-1)
                    
                    roll, pitch, yaw = self._rvec_to_euler_xyz(rvec)
                    distance = np.linalg.norm(tvec)
                    
                    detections[tag_id] = TagPose(
                        tag_id=tag_id,
                        tvec=tvec,
                        rvec=rvec,
                        roll=np.degrees(roll),
                        pitch=np.degrees(pitch),
                        yaw=np.degrees(yaw),
                        distance=distance
                    )
        
        # Update latest detections (thread-safe)
        with self.lock:
            self.latest_detections = detections
        
        return detections
    
    def get_tag_pose(self, tag_id: int) -> Optional[TagPose]:
        """
        Get the latest pose for a specific tag ID.
        
        Args:
            tag_id: AprilTag ID to look up
            
        Returns:
            TagPose if found, None otherwise
        """
        with self.lock:
            return self.latest_detections.get(tag_id)
    
    def draw_detections(self, frame: np.ndarray, detections: Dict[int, TagPose]) -> np.ndarray:
        """
        Draw detected tags and their poses on frame.
        
        Args:
            frame: Input frame
            detections: Dictionary of detected tags
            
        Returns:
            Annotated frame
        """
        # Get corners for drawing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            for i, corner in enumerate(corners):
                tag_id = int(ids[i])
                if tag_id in detections:
                    pose = detections[tag_id]
                    
                    # Draw coordinate axes
                    cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs,
                                     pose.rvec, pose.tvec, self.tag_size * 0.5)
                    
                    # Draw text info
                    c = corner.reshape(-1, 2)
                    x_text, y_text = int(c[0,0]), int(c[0,1]) - 10
                    
                    lines = [
                        f"id={tag_id}",
                        f"r={pose.roll:+.1f}°, p={pose.pitch:+.1f}°, y={pose.yaw:+.1f}°",
                        f"dx={pose.tvec[0]:+.3f}m, dy={pose.tvec[1]:+.3f}m, dz={pose.tvec[2]:+.3f}m"
                    ]
                    
                    for k, line in enumerate(lines):
                        yy = y_text - 20 * k
                        cv2.putText(frame, line, (x_text, max(yy, 15)),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
        
        return frame