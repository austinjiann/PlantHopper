import cv2
import numpy as np
import argparse
from pathlib import Path
import serial
import time

ser = serial.Serial("/dev/tty.usbserial-A50285BI", 115200, timeout=1, write_timeout=1)
time.sleep(3)

def send_cmd_line(dx_m: float, pitch_deg: float):
    # Build: cmd:search;id:num;found:bool;dx:num;pitch:deg;shoot:bool
    line = (
        f"cmd:SHOOT;"
        f"dx:{dx_m:.3f};"
        f"pitch:{int(round(pitch_deg))};"
    )
    try:
        print(line)
        ser.write(line.encode())
        # time.sleep(0.3)
    except Exception as e:
        # Non-fatal: print once per issue if needed
        print(f"[SERIAL WRITE ERROR] {e}")

def load_calibration(calib_path: str):
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
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--dict", type=str, default="DICT_APRILTAG_36h11")
    ap.add_argument("--tag-size", type=float, default=0.072)
    ap.add_argument("--calib", type=str, default="/Users/jliu61/Documents/GitHub/PlantHopper/CV/logitech_config.yaml")
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {args.cam}")

    if not hasattr(cv2, "aruco"):
        raise ImportError("cv2.aruco not found. Install: pip install opencv-contrib-python")

    try:
        dictionary_id = getattr(cv2.aruco, args.dict)
    except AttributeError:
        raise ValueError(f"Unknown dictionary '{args.dict}'. Try DICT_APRILTAG_36h11 or DICT_APRILTAG_25h9.")

    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dictionary, params)

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
                    rvec = rvec.reshape(-1)
                    tvec = tvec.reshape(-1)

                    cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, args.tag_size * 0.5)

                    roll, pitch, yaw = rvec_to_euler_xyz(rvec)
                    rpy_deg = np.degrees([roll, pitch, yaw])

                    c = corners[i].reshape(-1, 2)
                    x_text, y_text = int(c[0,0]), int(c[0,1]) - 10
                    tag_id = int(ids[i])

                    lines = [f"id={tag_id}"] + format_pose_text(rpy_deg, tvec)
                    for k, line in enumerate(lines):
                        yy = y_text - 20 * k
                        cv2.putText(frame, line, (x_text, max(yy, 15)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

                    # ===== SERIAL MESSAGE ON ID == 1 =====
                    if tag_id == 1:
                        dx_m = float(tvec[0])                 # camera X (meters)
                        pitch_deg = float(rpy_deg[1])         # pitch in degrees
                        send_cmd_line(dx_m=dx_m, pitch_deg=pitch)
                        
            else:
                cv2.putText(frame, "Provide --calib to compute pose (rpy/dx/dy).",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "No AprilTags detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("AprilTag Detector", frame)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
