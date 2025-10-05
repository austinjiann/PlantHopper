"""
Main integrated system for PlantHopper.
Combines AprilTag detection, Firebase integration, and Arduino control.
Uses a global `ser` (pyserial) for all serial I/O and a strict time-based WATER worker.
"""

import cv2
import numpy as np
import argparse
import threading
import time
import serial
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional

# Your detector wrapper: must expose AprilTagDetector with:
#   .detect_tags(frame) -> dict[tag_id] = pose (with .tvec, .roll, .pitch, .yaw, .distance)
#   .draw_detections(frame, detections) -> frame
from modules.apriltag_detector import AprilTagDetector


# ============================ Global serial ============================
ser = serial.Serial("/dev/tty.usbserial-A50285BI", 115200, timeout=1, write_timeout=1)
time.sleep(2.5)  # let Arduino reset after opening the port
SER_LOCK = threading.Lock()
# ======================================================================

# Global flag for graceful shutdown
running = True

# For console change-detection prints in camera loop
previous_tag_states = {}

# Shared (thread-safe) detection snapshot for other threads
_detection_lock = threading.Lock()
# Map[int tag_id] -> {"tvec": np.ndarray shape(3,), "roll": float, "pitch": float, "yaw": float, "distance": float}
latest_detections = {}


# ----------------------------- Serial helpers -----------------------------
def _serial_write_line(line: str) -> bool:
    """Thread-safe write to the global `ser`."""
    try:
        with SER_LOCK:
            ser.write(line.encode())
        return True
    except Exception as e:
        print(f"[SERIAL WRITE ERROR] {e}")
        return False


def _send_cmd_water(found: bool, dx_m: float, pitch_deg: float, sweep_s: Optional[float] = None):
    """
    Format:
      cmd:WATER;found:bool;dx:num;pitch:deg;[sweep:seconds;]
    """
    parts = [
        "cmd:WATER",
        f"found:{str(found).lower()}",
        f"dx:{dx_m:.3f}",
        f"pitch:{int(round(pitch_deg))}",
    ]
    if sweep_s is not None:
        try:
            parts.append(f"sweep:{int(round(max(0.0, float(sweep_s))))}")
        except Exception:
            pass
    line = ";".join(parts) + ";\n"
    print(line.strip())
    _serial_write_line(line)


def _send_cmd_track(tag_id: int, found: bool, dx_m: float, pitch_deg: float, shoot: bool = False):
    """
    Format:
      cmd:TRACK;id:num;found:bool;dx:num;pitch:deg;shoot:bool
    """
    line = (
        f"cmd:TRACK;"
        f"id:{int(tag_id)};"
        f"found:{str(found).lower()};"
        f"dx:{dx_m:.3f};"
        f"pitch:{int(round(pitch_deg))};"
        f"shoot:{str(shoot).lower()}\n"
    )
    print(line.strip())
    _serial_write_line(line)
# --------------------------------------------------------------------------


# ---------------- Moisture reading helpers (match UniversalControl.ino) ----------------
def _parse_kv_line(line: str):
    """Parse 'key:value;key:value;...' into a dict; keys are lowercased."""
    kv = {}
    for part in line.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip().lower()] = v.strip()
    return kv


def _read_moisture_snapshot(seconds: float = 3.0):
    """
    Read Arduino serial for a short window and collect latest moisture per sensor:
      cmd:MOISTURE;id:sensor_3;percent:0.6
    Returns: dict {sensor_label(str): percent_float (0..1)}
    """
    data = {}
    deadline = time.time() + max(0.5, seconds)
    while time.time() < deadline:
        try:
            with SER_LOCK:
                raw = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception as e:
            print(f"[Sensor] Serial read error: {e}")
            break
        if not raw:
            continue
        print(raw)  # debug

        kv = _parse_kv_line(raw)
        if not kv or kv.get("cmd", "").upper() != "MOISTURE":
            continue

        label = kv.get("id", "")
        pct_s = kv.get("percent", "")
        if not label or not pct_s:
            continue

        sensor_label = label.strip().lower()
        try:
            pct = float(pct_s)
        except ValueError:
            continue
        if pct > 1.0:  # accept 0..100 and convert to 0..1
            pct = pct / 100.0

        data[sensor_label] = pct

    return data
# --------------------------------------------------------------------------------------


# ============================ Firebase Thread ============================
def firebase_thread(firebase_cred_path: str, plant_tag_mapping: dict):
    """
    Firebase listener thread with strict time-based WATER behavior:
      - SCAN: send found:false at WATER_SEND_HZ for exactly waterScanSeconds (or until tag detected)
      - FIRE: upon detection, send found:true at WATER_SEND_HZ for exactly waterFireSeconds, then finish
    """
    global running
    doc_watch = None

    try:
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[Firebase] Firebase initialized.")

        def water_worker(plant_id: str, target_tag_id: int,
                         send_hz: float, scan_seconds: float, fire_seconds: float,
                         default_pitch: float):
            """Enforce timing with wall-clock deadlines; cadence independent of camera/detections rate."""
            nonlocal db
            dt = 1.0 / max(send_hz, 1e-6)
            scan_end = time.time() + max(0.0, scan_seconds)
            fire_end = None

            last_pitch_deg = float(default_pitch)
            success = False

            next_send = time.time()  # rate limiter tick

            print(f"[Water] SCAN start: {scan_seconds:.1f}s @ {send_hz:.1f} Hz (plant={plant_id}, tag={target_tag_id})")
            while running:
                now = time.time()

                # If still scanning and time is up -> stop (no detection)
                if fire_end is None and now >= scan_end:
                    print("[Water] SCAN timeout (no detection).")
                    break

                # Send at exact cadence
                if now >= next_send:
                    if fire_end is None:
                        # SCAN PHASE
                        with _detection_lock:
                            pose = latest_detections.get(int(target_tag_id), None)

                        if pose is None:
                            remaining = max(0.0, scan_end - now)
                            _send_cmd_water(found=False, dx_m=0.0,
                                            pitch_deg=last_pitch_deg, sweep_s=remaining)
                        else:
                            # Transition to FIRE
                            dx_m = float(pose["tvec"][0])
                            pitch_deg = float(pose["pitch"])
                            last_pitch_deg = pitch_deg
                            fire_end = now + max(0.0, fire_seconds)
                            print(f"[Water] DETECTED. Enter FIRE: {fire_seconds:.1f}s")
                            _send_cmd_water(found=True, dx_m=dx_m, pitch_deg=pitch_deg, sweep_s=0)

                        next_send += dt
                    else:
                        # FIRE PHASE
                        with _detection_lock:
                            pose_now = latest_detections.get(int(target_tag_id), None)
                        if pose_now is None:
                            _send_cmd_water(found=True, dx_m=0.0,
                                            pitch_deg=last_pitch_deg, sweep_s=0)
                        else:
                            dx_m = float(pose_now["tvec"][0])
                            pitch_deg = float(pose_now["pitch"])
                            last_pitch_deg = pitch_deg
                            _send_cmd_water(found=True, dx_m=dx_m, pitch_deg=pitch_deg, sweep_s=0)
                        next_send += dt

                # Finish when fire window ends
                if fire_end is not None and now >= fire_end:
                    success = True
                    print("[Water] FIRE complete.")
                    break

                time.sleep(0.001)  # tiny sleep to avoid tight spin

            # Report to Firestore
            if success:
                db.collection("plants").document(plant_id).update({
                    "command": None,
                    "lastWatered": firestore.SERVER_TIMESTAMP,
                    "wateringSuccess": True
                })
            else:
                db.collection("plants").document(plant_id).update({
                    "command": None,
                    "wateringSuccess": False,
                    "error": "Target not found before scan timeout"
                })
            print("[Water] Session finished.\n")

        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                data = doc.to_dict()
                plant_id = doc.id
                command = data.get("command")
                if not command:
                    continue

                if command == "water":
                    target_tag_id = plant_tag_mapping.get(plant_id)
                    if target_tag_id is None:
                        print(f"[Firebase] No AprilTag mapping for plant {plant_id}")
                        db.collection("plants").document(plant_id).update({
                            "command": None,
                            "wateringSuccess": False,
                            "error": "No AprilTag mapping found"
                        })
                        continue

                    send_hz       = float(data.get("waterSendHz", 10.0))
                    scan_seconds  = float(data.get("waterScanSeconds", 17.0))
                    fire_seconds  = float(data.get("waterFireSeconds", 14.0))
                    default_pitch = float(data.get("waterPitchDeg", 0.0))

                    # Clear command immediately (UI responsiveness) and launch worker
                    db.collection("plants").document(plant_id).update({"command": None})
                    threading.Thread(
                        target=water_worker,
                        args=(plant_id, int(target_tag_id), send_hz, scan_seconds, fire_seconds, default_pitch),
                        daemon=True
                    ).start()

                elif command == "scan":
                    # Simple time-based tracker (left similar to your earlier behavior)
                    target_tag_id = plant_tag_mapping.get(plant_id)
                    if target_tag_id is None:
                        db.collection("plants").document(plant_id).update({
                            "command": None,
                            "trackingSuccess": False,
                            "error": "No AprilTag mapping found"
                        })
                        continue

                    TRACK_SEND_HZ = float(data.get("trackSendHz", 20.0))
                    TRACK_SECONDS = float(data.get("trackSeconds", 15.0))
                    DEFAULT_PITCH = float(data.get("trackPitchDeg", 0.0))

                    dt = 1.0 / max(TRACK_SEND_HZ, 1e-6)
                    until = time.time() + max(TRACK_SECONDS, 0.5)
                    print(f"[Firebase] TRACK {target_tag_id} for {TRACK_SECONDS:.1f}s @ {TRACK_SEND_HZ:.1f} Hz.")
                    sent_any = False
                    while running and time.time() < until:
                        with _detection_lock:
                            pose = latest_detections.get(int(target_tag_id), None)
                        if pose is None:
                            _send_cmd_track(tag_id=int(target_tag_id), found=False,
                                            dx_m=0.0, pitch_deg=DEFAULT_PITCH, shoot=False)
                        else:
                            dx_m = float(pose["tvec"][0])
                            pitch_deg = float(pose["pitch"])
                            _send_cmd_track(tag_id=int(target_tag_id), found=True,
                                            dx_m=dx_m, pitch_deg=pitch_deg, shoot=False)
                            sent_any = True
                        time.sleep(dt)

                    db.collection("plants").document(plant_id).update({
                        "command": None,
                        "lastTracked": firestore.SERVER_TIMESTAMP,
                        "trackingSuccess": sent_any
                    })
                    print("[Firebase] TRACK complete.\n")

                elif command == "sensor":
                    print("[Firebase] Reading moisture snapshot...")
                    readings = _read_moisture_snapshot(seconds=3.0)
                    db.collection("plants").document(plant_id).update({
                        "command": None,
                        "lastScanned": firestore.SERVER_TIMESTAMP
                    })
                    if not readings:
                        print("[Firebase] No MOISTURE lines captured.")
                        db.collection("plants").document(plant_id).update({
                            "sensorReadSuccess": False,
                            "error": "No MOISTURE lines captured"
                        })
                        continue

                    plants_ref = db.collection("plants")
                    any_written = False
                    for sensor_label, moisture_value in readings.items():
                        try:
                            query = plants_ref.where("sensorId", "==", sensor_label).stream()
                            matched = False
                            for plant_doc in query:
                                matched = True
                                any_written = True
                                print(f"[Firebase] {sensor_label} ({moisture_value:.3f}) → Plant {plant_doc.id}")
                                db.collection("moisturedata").document(plant_doc.id).collection("readings").add({
                                    "timestamp": firestore.SERVER_TIMESTAMP,
                                    "moisture": float(moisture_value)
                                })
                            if not matched:
                                print(f"[Firebase] No plant found for sensorId '{sensor_label}'.")
                        except Exception as e:
                            print(f"[Firebase] Error writing {sensor_label}: {e}")

                    db.collection("plants").document(plant_id).update({
                        "sensorReadSuccess": any_written
                    })

        doc_ref = db.collection("plants")
        doc_watch = doc_ref.on_snapshot(on_snapshot)

        print("[Firebase] Listening for changes...")
        while running:
            time.sleep(0.5)

    except Exception as e:
        print(f"[Firebase] Error: {e}")
        import traceback
        traceback.print_exc()
        running = False

    finally:
        if doc_watch is not None:
            try:
                doc_watch.unsubscribe()
            except:
                pass
        print("[Firebase] Firebase listener stopped.")
# =======================================================================


# ============================ Camera / Detection ============================
def run_camera(args, detector: AprilTagDetector, cap: cv2.VideoCapture):
    """
    Run AprilTag detection in the main thread (required for OpenCV GUI).
    Populates `latest_detections` each frame for the Firebase thread.
    """
    global running, previous_tag_states, latest_detections

    POSITION_THRESHOLD = 0.01  # 1 cm
    ROTATION_THRESHOLD = 2.0   # 2 degrees

    print("[Camera] Press Q to quit.")
    try:
        while running:
            ok, frame = cap.read()
            if not ok:
                print("[Camera] Failed to grab frame.")
                break

            # Detect tags
            detections = detector.detect_tags(frame)

            # Clear & repopulate shared detection snapshot
            with _detection_lock:
                latest_detections.clear()

            if detections:
                # Draw detections
                frame = detector.draw_detections(frame, detections)

                for tag_id, pose in detections.items():
                    # Update shared snapshot (pose.pitch expected in degrees)
                    with _detection_lock:
                        latest_detections[int(tag_id)] = {
                            "tvec": pose.tvec.copy(),
                            "roll": float(pose.roll),
                            "pitch": float(pose.pitch),
                            "yaw": float(pose.yaw),
                            "distance": float(pose.distance),
                        }

                    should_print = False
                    if tag_id not in previous_tag_states:
                        should_print = True
                        print(f"\n[Camera] New tag detected: ID {tag_id}")
                    else:
                        prev = previous_tag_states[tag_id]
                        pos_change = np.linalg.norm(pose.tvec - prev['tvec'])
                        rot_change = max(
                            abs(pose.roll - prev['roll']),
                            abs(pose.pitch - prev['pitch']),
                            abs(pose.yaw - prev['yaw'])
                        )
                        if pos_change > POSITION_THRESHOLD:
                            should_print = True
                            print(f"\n[Camera] Tag {tag_id} position changed by {pos_change:.4f} m")
                        elif rot_change > ROTATION_THRESHOLD:
                            should_print = True
                            print(f"\n[Camera] Tag {tag_id} rotation changed by {rot_change:.2f}°")

                    previous_tag_states[tag_id] = {
                        'tvec': pose.tvec.copy(),
                        'roll': pose.roll,
                        'pitch': pose.pitch,
                        'yaw': pose.yaw
                    }

                    if should_print:
                        print(f"  ID: {tag_id}")
                        print(f"  Position (x, y, z): ({pose.tvec[0]:+.4f}, {pose.tvec[1]:+.4f}, {pose.tvec[2]:+.4f}) m")
                        print(f"  Distance: {pose.distance:.4f} m")
                        print(f"  Rotation (r, p, y): ({pose.roll:+.2f}°, {pose.pitch:+.2f}°, {pose.yaw:+.2f}°)")
            else:
                cv2.putText(frame, "No AprilTags detected", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

            cv2.imshow("AprilTag Detector", frame)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
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
        print("[Camera] Camera stopped.")
# =======================================================================


# ================================== Main ==================================
def main():
    global running

    ap = argparse.ArgumentParser(description="PlantHopper (global ser, time-based WATER)")
    ap.add_argument("--cam", type=int, default=0, help="Camera index (default 0)")
    ap.add_argument("--width", type=int, default=1920, help="Capture width")
    ap.add_argument("--height", type=int, default=1080, help="Capture height")
    ap.add_argument("--dict", type=str, default="DICT_APRILTAG_36h11",
                    help="Tag dictionary (e.g., DICT_APRILTAG_36h11, DICT_APRILTAG_25h9)")
    ap.add_argument("--tag-size", type=float, default=0.038,
                    help="Tag size in meters (edge length)")
    ap.add_argument("--calib", type=str, default="./Firebase/logitech_config.yaml",
                    help="Path to camera calibration file")
    ap.add_argument("--firebase-cred", type=str,
                    default="./Firebase/planthopper-2fbc8-firebase-adminsdk-fbsvc-bf21b9e16e.json",
                    help="Path to Firebase credentials JSON")
    args = ap.parse_args()

    print("=" * 60)
    print("PlantHopper System Starting (global ser, time-based WATER)")
    print("=" * 60)
    print("Press Q in the camera window or Ctrl+C to stop.\n")

    # Plant → AprilTag mapping
    plant_tag_mapping = {
        "plant1": 1,
        "plant2": 2,
        "plant3": 3,
        "plant4": 4,
        "plant5": 5,
        # Add more mappings as needed
    }

    try:
        # Initialize detector
        detector = AprilTagDetector(
            calib_path=args.calib,
            tag_size=args.tag_size,
            dict_name=args.dict
        )

        # Initialize camera
        cap = cv2.VideoCapture(args.cam)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {args.cam}")

        print("[Main] All systems initialized successfully\n")

        # Start Firebase listener
        fb_thread = threading.Thread(
            target=firebase_thread,
            args=(args.firebase_cred, plant_tag_mapping),
            daemon=True
        )
        fb_thread.start()

        # Run camera in main thread (OpenCV GUI requirement)
        run_camera(args, detector, cap)

    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt detected. Stopping...")
        running = False
    except Exception as e:
        print(f"[Main] Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        running = False
    finally:
        print("\n[Main] Shutting down...")
        running = False

        # Wait briefly for Firebase thread to finish
        if 'fb_thread' in locals():
            print("[Main] Waiting for Firebase thread to stop...]")
            fb_thread.join(timeout=2)

        # Release camera
        if 'cap' in locals():
            cap.release()

        # Close OpenCV windows
        try:
            cv2.destroyAllWindows()
        except:
            pass

        # Close global serial
        try:
            with SER_LOCK:
                if ser and ser.is_open:
                    ser.close()
        except:
            pass

        print("[Main] Program terminated.")
        print("=" * 60)


if __name__ == "__main__":
    main()
