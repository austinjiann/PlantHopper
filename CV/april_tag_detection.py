import cv2
import numpy as np
import argparse
from pathlib import Path

def load_calibration(calib_path: str):
    """
    Load OpenCV calibration YAML/JSON saved via cv2.FileStorage.
    Expects keys: camera_matrix, dist_coeffs
    """
    fs = cv2.FileStorage(calib_path, cv2.FILE_STORAGE_READ)
    if not fs.isOpened():
        raise FileNotFoundError(f"Could not open calibration file: {calib_path}")
    camera_matrix = fs.getNode("camera_matrix").mat()
    dist_coeffs = fs.getNode("dist_coeffs").mat()
    fs.release()
    if camera_matrix is None or dist_coeffs is None:
        raise ValueError("Calibration file missing 'camera_matrix' or 'dist_coeffs'.")
    return camera_matrix, dist_coeffs

def rvec_to_euler_xyz(rvec: np.ndarray):
    """
    Convert OpenCV Rodrigues rvec to Euler angles (roll, pitch, yaw) in radians,
    using X (roll) -> Y (pitch) -> Z (yaw) intrinsic rotations (XYZ).
    """
    R, _ = cv2.Rodrigues(rvec)
    sy = np.sqrt(R[0,0]*R[0,0] + R[1,0]*R[1,0])
    singular = sy < 1e-6

    if not singular:
        roll  = np.arctan2(R[2,1], R[2,2])     # x
        pitch = np.arctan2(-R[2,0], sy)        # y
        yaw   = np.arctan2(R[1,0], R[0,0])     # z
    else:
        roll  = np.arctan2(-R[1,2], R[1,1])
        pitch = np.arctan2(-R[2,0], sy)
        yaw   = 0.0
    return roll, pitch, yaw

def format_pose_text(rpy_deg, tvec):
    r_deg, p_deg, y_deg = rpy_deg
    dx, dy, dz = tvec
    return [
        f"r={r_deg:+.1f}°, p={p_deg:+.1f}°, y={y_deg:+.1f}°",
        f"dx={dx:+.3f} m, dy={dy:+.3f} m, dz={dz:+.3f} m",
    ]

def main():
    ap = argparse.ArgumentParser(description="AprilTag detection (OpenCV)")
    ap.add_argument("--cam", type=int, default=0, help="Camera index (default 0)")
    ap.add_argument("--width", type=int, default=1920, help="Capture width")
    ap.add_argument("--height", type=int, default=1080, help="Capture height")
    ap.add_argument("--dict", type=str, default="DICT_APRILTAG_36h11",
                    help="Tag dictionary (e.g., DICT_APRILTAG_36h11, DICT_APRILTAG_25h9)")
    ap.add_argument("--tag-size", type=float, default=0.08,
                    help="Tag size in meters (edge length) for pose estimation")
    ap.add_argument("--calib", type=str, default="/Users/jliu61/Documents/GitHub/PlantHopper/CV/logitech_config.yaml",
                    help="Path to camera calibration file (YAML/JSON) with camera_matrix & dist_coeffs")
    args = ap.parse_args()

    # ----- Camera -----
    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {args.cam}")

    # ----- Dictionary & Detector -----
    if not hasattr(cv2, "aruco"):
        raise ImportError("cv2.aruco not found. Install: pip install opencv-contrib-python")

    try:
        dictionary_id = getattr(cv2.aruco, args.dict)
    except AttributeError:
        raise ValueError(f"Unknown dictionary '{args.dict}'. "
                         f"Try DICT_APRILTAG_36h11 or DICT_APRILTAG_25h9.")

    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dictionary, params)

    # ----- Optional calibration -----
    camera_matrix = None
    dist_coeffs = None
    if args.calib:
        camera_matrix, dist_coeffs = load_calibration(args.calib)
        print("Loaded calibration.")

    print("Press Q to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Failed to grab frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            if camera_matrix is not None and dist_coeffs is not None:
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                    corners, args.tag_size, camera_matrix, dist_coeffs
                )
                for i, (rvec, tvec) in enumerate(zip(rvecs, tvecs)):
                    # Flatten shapes like (1,3) -> (3,)
                    rvec = rvec.reshape(-1)
                    tvec = tvec.reshape(-1)  # [dx, dy, dz] in meters (camera coordinates)

                    # Draw axes
                    cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, args.tag_size * 0.5)

                    # Compute RPY (deg)
                    roll, pitch, yaw = rvec_to_euler_xyz(rvec)
                    rpy_deg = np.degrees([roll, pitch, yaw])

                    # Overlay text near the first corner of the marker
                    c = corners[i].reshape(-1, 2)  # (4,2)
                    x_text, y_text = int(c[0,0]), int(c[0,1]) - 10

                    lines = [f"id={int(ids[i])}"] + format_pose_text(rpy_deg, tvec)
                    for k, line in enumerate(lines):
                        yy = y_text - 20 * k
                        cv2.putText(frame, line, (x_text, max(yy, 15)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "Provide --calib to compute pose (rpy/dx/dy).",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "No AprilTags detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)


        # Intrinsics from your YAML
        cx, cy = camera_matrix[0,2], camera_matrix[1,2]
        fx, fy = camera_matrix[0,0], camera_matrix[1,1]

        # Tag pixel center vs principal point
        c = corners[i].reshape(-1, 2)
        u, v = c.mean(axis=0)

        z = float(tvec[2])
        x_from_px = (u - cx) * z / fx  # meters predicted from pixels
        y_from_px = (v - cy) * z / fy

        print(f"u-cx={u-cx:.1f}px  v-cy={v-cy:.1f}px  "
            f"tvec=({tvec[0]:.3f},{tvec[1]:.3f},{tvec[2]:.3f})  "
            f"x_from_px={x_from_px:.3f}  y_from_px={y_from_px:.3f}")

        cv2.imshow("AprilTag Detector", frame)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
