import cv2
import numpy as np
import argparse
from pathlib import Path
import threading
import time
import firebase_admin
from firebase_admin import credentials, firestore


# Global flag for graceful shutdown
running = True

# Store previous tag states for change detection
previous_tag_states = {}



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
        roll  = np.arctan2(R[2,1], R[2,2])
        pitch = np.arctan2(-R[2,0], sy)
        yaw   = np.arctan2(R[1,0], R[0,0])
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

def firebase_thread(firebase_cred_path):
    """
    Thread function for Firebase listener
    """
    global running
    
    doc_watch = None
    try:
        # Initialize Firebase
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[Firebase] Firebase initialized.")

        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                data = doc.to_dict()
                if data.get("command") == "water":
                    print(f"[Firebase] Watering {doc.id}!")
                    # TODO: send serial command to Arduino
                    # reset command
                    db.collection("plants").document(doc.id).update({
                        "command": None,
                        "lastWatered": firestore.SERVER_TIMESTAMP
                    })

                    db.collection("moisturedata").document(doc.id).collection("readings").add({
                        "timestamp": firestore.SERVER_TIMESTAMP,
                        "moisture": 0.3
                    })

                    
                elif data.get("command") == "sweep":
                    print(f"[Firebase] Sweeping {doc.id}!")
                    # TODO: send serial command to Arduino
                    # reset command
                    db.collection("plants").document(doc.id).update({
                        "command": None,
                        "lastSwept": firestore.SERVER_TIMESTAMP
                    })

                # Basically, we want to 
                # 1) Get the sensor data from arduino
                # 2) Determine which plant it belongs to
                # 3) Update the moisture column for that plant id
                elif data.get("command") == "sensor":
                    print("[Firebase] Processing sensor data...")

                    # Example: data might look like {"command": "sensor", "sensorId": "sensor_1", "moisture": 0.3}
                    sensor_id = data.get("sensorId")
                    moisture_value = data.get("moisture")

                    if not sensor_id or moisture_value is None:
                        print("[Error] Missing sensorId or moisture value.")
                    else:
                        # Find which plant corresponds to this sensor
                        plants_ref = db.collection("plants")
                        query = plants_ref.where("sensorId", "==", sensor_id).stream()

                        found = False
                        for doc in query:
                            found = True
                            print(f"[Firebase] Sensor {sensor_id} → Plant {doc.id}")

                            db.collection("moisturedata").document(doc.id).collection("readings").add({
                                "timestamp": firestore.SERVER_TIMESTAMP,
                                "moisture": moisture_value
                            })

                            # optionally, update the latest moisture reading in plant doc
                            db.collection("plants").document(doc.id).update({
                                "latestMoisture": moisture_value,
                                "lastUpdated": firestore.SERVER_TIMESTAMP
                            })

                        if not found:
                            print(f"[Firebase] No plant found for sensor ID {sensor_id}.")


        doc_ref = db.collection("plants").document("plant1")
        doc_watch = doc_ref.on_snapshot(on_snapshot)

        print("[Firebase] Listening for changes...")
        while running:
            time.sleep(0.5)
        
    except Exception as e:
        print(f"[Firebase] Error: {e}")
        running = False
    
    finally:
        if doc_watch is not None:
            try:
                doc_watch.unsubscribe()
            except:
                pass
        print("[Firebase] Firebase listener stopped.")

def run_camera(args):
    """
    Run AprilTag detection in the main thread (required for OpenCV GUI)
    """
    global running, previous_tag_states
    
    # Threshold for detecting significant changes (in meters for position, degrees for rotation)
    POSITION_THRESHOLD = 0.01  # 1 cm
    ROTATION_THRESHOLD = 2.0   # 2 degrees
    
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
        try:
            camera_matrix, dist_coeffs = load_calibration(args.calib)
            print("[Camera] Loaded calibration.")
        except Exception as e:
            print(f"[Camera] Warning: Could not load calibration: {e}")

    print("[Camera] Press Q to quit.")
    
    try:
        while running:
            ok, frame = cap.read()
            if not ok:
                print("[Camera] Failed to grab frame.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            if ids is not None and len(ids) > 0:
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)

                if camera_matrix is not None and dist_coeffs is not None:
                    # Use the correct API for newer OpenCV versions
                    obj_points = np.array([
                        [-args.tag_size/2, args.tag_size/2, 0],
                        [args.tag_size/2, args.tag_size/2, 0],
                        [args.tag_size/2, -args.tag_size/2, 0],
                        [-args.tag_size/2, -args.tag_size/2, 0]
                    ], dtype=np.float32)
                    
                    rvecs = []
                    tvecs = []
                    for corner in corners:
                        success, rvec, tvec = cv2.solvePnP(
                            obj_points, corner, camera_matrix, dist_coeffs, 
                            flags=cv2.SOLVEPNP_IPPE_SQUARE
                        )
                        if success:
                            rvecs.append(rvec)
                            tvecs.append(tvec)
                    for i, (rvec, tvec) in enumerate(zip(rvecs, tvecs)):
                        rvec = rvec.reshape(-1)
                        tvec = tvec.reshape(-1)

                        cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, args.tag_size * 0.5)

                        roll, pitch, yaw = rvec_to_euler_xyz(rvec)
                        rpy_deg = np.degrees([roll, pitch, yaw])
                        
                        tag_id = int(ids[i])
                        
                        # Check if this is a new tag or if values have changed significantly
                        should_print = False
                        if tag_id not in previous_tag_states:
                            should_print = True
                            print(f"\n[Camera] New tag detected: ID {tag_id}")
                        else:
                            prev_state = previous_tag_states[tag_id]
                            # Check position changes
                            pos_change = np.linalg.norm(tvec - prev_state['tvec'])
                            # Check rotation changes
                            rot_change = np.max(np.abs(rpy_deg - prev_state['rpy_deg']))
                            
                            if pos_change > POSITION_THRESHOLD:
                                should_print = True
                                print(f"\n[Camera] Tag {tag_id} position changed by {pos_change:.4f}m")
                            elif rot_change > ROTATION_THRESHOLD:
                                should_print = True
                                print(f"\n[Camera] Tag {tag_id} rotation changed by {rot_change:.2f}°")
                        
                        # Update state
                        previous_tag_states[tag_id] = {
                            'tvec': tvec.copy(),
                            'rpy_deg': rpy_deg.copy()
                        }
                        
                        # Print detailed information if there was a change
                        if should_print:
                            print(f"  ID: {tag_id}")
                            print(f"  Position (x, y, z): ({tvec[0]:+.4f}, {tvec[1]:+.4f}, {tvec[2]:+.4f}) meters")
                            print(f"  Distance from camera: {np.linalg.norm(tvec):.4f} meters")
                            print(f"  Rotation (roll, pitch, yaw): ({rpy_deg[0]:+.2f}°, {rpy_deg[1]:+.2f}°, {rpy_deg[2]:+.2f}°)")

                        c = corners[i].reshape(-1, 2)
                        x_text, y_text = int(c[0,0]), int(c[0,1]) - 10

                        lines = [f"id={tag_id}"] + format_pose_text(rpy_deg, tvec)
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

            cv2.imshow("AprilTag Detector", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q')):
                running = False
                break
    
    except KeyboardInterrupt:
        print("\n[Camera] Keyboard interrupt in camera loop.")
        running = False
    
    except Exception as e:
        print(f"[Camera] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        running = False
    
    finally:
        # Clean up camera resources
        cap.release()
        cv2.destroyAllWindows()
        print("[Camera] Camera stopped.")

def main():
    global running
    
    ap = argparse.ArgumentParser(description="AprilTag detection with Firebase listener")
    ap.add_argument("--cam", type=int, default=0, help="Camera index (default 0)")
    ap.add_argument("--width", type=int, default=1280, help="Capture width")
    ap.add_argument("--height", type=int, default=720, help="Capture height")
    ap.add_argument("--dict", type=str, default="DICT_APRILTAG_36h11",
                    help="Tag dictionary (e.g., DICT_APRILTAG_36h11, DICT_APRILTAG_25h9)")
    ap.add_argument("--tag-size", type=float, default=0.08,
                    help="Tag size in meters (edge length) for pose estimation")
    ap.add_argument("--calib", type=str, default="./Firebase/logitech_config.yaml",
                    help="Path to camera calibration file (YAML/JSON) with camera_matrix & dist_coeffs")
    ap.add_argument("--firebase-cred", type=str, 
                    default="./Firebase/planthopper-2fbc8-firebase-adminsdk-fbsvc-bf21b9e16e.json",
                    help="Path to Firebase credentials JSON file")
    args = ap.parse_args()

    print("Starting AprilTag Detection + Firebase Listener")
    print("Press Q in the camera window or Ctrl+C to stop.\n")

    # Start Firebase listener in background thread
    fb_thread = threading.Thread(target=firebase_thread, args=(args.firebase_cred,), daemon=True)
    fb_thread.start()
    
    # Give Firebase thread a moment to initialize
    time.sleep(1)

    # Run camera in main thread (required for OpenCV GUI to work properly)
    try:
        run_camera(args)
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt detected. Stopping...")
        running = False
    
    # Wait for Firebase thread to finish
    print("[Main] Waiting for Firebase thread to stop...")
    fb_thread.join(timeout=2)
    
    print("[Main] Program terminated.")

if __name__ == "__main__":
    main()