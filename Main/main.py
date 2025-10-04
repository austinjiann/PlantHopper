"""
Main integrated system for PlantHopper.
Combines AprilTag detection, Firebase integration, and Arduino control.
"""
import cv2
import numpy as np
import argparse
import threading
import time
import firebase_admin
from firebase_admin import credentials, firestore

from modules.arduino_controller import ArduinoController
from modules.apriltag_detector import AprilTagDetector
from modules.shooting_system import ShootingSystem


# Global flag for graceful shutdown
running = True

# Store previous tag states for change detection (for camera display)
previous_tag_states = {}


def firebase_thread(firebase_cred_path: str, shooting_system: ShootingSystem,
                    cap: cv2.VideoCapture, plant_tag_mapping: dict):
    """
    Thread function for Firebase listener.
    Handles water, sweep, and sensor commands from Firebase.
    
    Args:
        firebase_cred_path: Path to Firebase credentials JSON
        shooting_system: ShootingSystem instance for executing actions
        cap: Video capture object (shared with main thread)
        plant_tag_mapping: Dict mapping plant IDs to AprilTag IDs
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
            """Handle Firebase document changes."""
            for doc in doc_snapshot:
                data = doc.to_dict()
                plant_id = doc.id
                command = data.get("command")
                
                if not command:
                    continue  # Skip if no command
                
                if command == "water":
                    print(f"\n[Firebase] ===== WATER COMMAND for {plant_id} =====")
                    
                    # Get target AprilTag ID for this plant
                    target_tag_id = plant_tag_mapping.get(plant_id)
                    
                    if target_tag_id is None:
                        print(f"[Firebase] Error: No AprilTag mapping for plant {plant_id}")
                        db.collection("plants").document(plant_id).update({
                            "command": None,
                            "error": "No AprilTag mapping found"
                        })
                        continue
                    
                    print(f"[Firebase] Target AprilTag ID: {target_tag_id}")
                    
                    # Execute 3 cycles of sweep and shoot
                    success = shooting_system.sweep_search_shoot_cycle(
                        target_tag_id=target_tag_id,
                        cap=cap,
                        max_cycles=3
                    )
                    
                    # Update Firebase with result
                    if success:
                        print(f"[Firebase] Successfully watered {plant_id}")
                        db.collection("plants").document(plant_id).update({
                            "command": None,
                            "lastWatered": firestore.SERVER_TIMESTAMP,
                            "wateringSuccess": True
                        })
                    else:
                        print(f"[Firebase] Failed to water {plant_id} - target not found")
                        db.collection("plants").document(plant_id).update({
                            "command": None,
                            "wateringSuccess": False,
                            "error": "Target AprilTag not found after 3 sweep cycles"
                        })
                    
                    print(f"[Firebase] ===== WATER COMMAND COMPLETE =====\n")


                #code for tracking a plant
                elif command == "scan":
                    print(f"[Firebase] Sweeping {plant_id}!")
                    shooting_system.arduino.sweep()
                    db.collection("plants").document(plant_id).update({
                        "command": None,
                        "lastSwept": firestore.SERVER_TIMESTAMP
                    })

                elif command == "sensor":
                    print("[Firebase] Processing sensor data...")
                    
                    # TODO: Get actual sensor data from Arduino
                    # For now using placeholder values
                    sensor_id = data.get("sensorId", 8)
                    moisture_value = data.get("moisture", 0.9)

                    db.collection("plants").document(plant_id).update({
                        "command": None,
                        "lastScanned": firestore.SERVER_TIMESTAMP
                    })

                    if moisture_value is None:
                        print("[Firebase] Error: Missing moisture value.")
                    else:
                        # Find which plant corresponds to this sensor
                        plants_ref = db.collection("plants")
                        query = plants_ref.where("sensorId", "==", sensor_id).stream()

                        found = False
                        for plant_doc in query:
                            found = True
                            print(f"[Firebase] Sensor {sensor_id} → Plant {plant_doc.id}")

                            # Add moisture reading to subcollection
                            db.collection("moisturedata").document(plant_doc.id).collection("readings").add({
                                "timestamp": firestore.SERVER_TIMESTAMP,
                                "moisture": moisture_value
                            })

                        if not found:
                            print(f"[Firebase] No plant found for sensor ID {sensor_id}.")

        # Listen to all plants or specific plant
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


def run_camera(args, shooting_system: ShootingSystem, cap: cv2.VideoCapture):
    """
    Run AprilTag detection in the main thread (required for OpenCV GUI).
    
    Args:
        args: Command line arguments
        shooting_system: ShootingSystem instance
        cap: Video capture object (shared with Firebase thread)
    """
    global running, previous_tag_states
    
    detector = shooting_system.detector
    
    # Threshold for detecting significant changes (for display purposes)
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

            if detections:
                # Draw detections on frame
                frame = detector.draw_detections(frame, detections)
                
                # Check for significant changes (for console output)
                for tag_id, pose in detections.items():
                    should_print = False
                    
                    if tag_id not in previous_tag_states:
                        should_print = True
                        print(f"\n[Camera] New tag detected: ID {tag_id}")
                    else:
                        prev_state = previous_tag_states[tag_id]
                        pos_change = np.linalg.norm(pose.tvec - prev_state['tvec'])
                        rot_change = max(
                            abs(pose.roll - prev_state['roll']),
                            abs(pose.pitch - prev_state['pitch']),
                            abs(pose.yaw - prev_state['yaw'])
                        )
                        
                        if pos_change > POSITION_THRESHOLD:
                            should_print = True
                            print(f"\n[Camera] Tag {tag_id} position changed by {pos_change:.4f}m")
                        elif rot_change > ROTATION_THRESHOLD:
                            should_print = True
                            print(f"\n[Camera] Tag {tag_id} rotation changed by {rot_change:.2f}°")
                    
                    # Update state
                    previous_tag_states[tag_id] = {
                        'tvec': pose.tvec.copy(),
                        'roll': pose.roll,
                        'pitch': pose.pitch,
                        'yaw': pose.yaw
                    }
                    
                    # Print detailed information if there was a change
                    if should_print:
                        print(f"  ID: {tag_id}")
                        print(f"  Position (x, y, z): ({pose.tvec[0]:+.4f}, {pose.tvec[1]:+.4f}, {pose.tvec[2]:+.4f}) meters")
                        print(f"  Distance: {pose.distance:.4f} meters")
                        print(f"  Rotation (r, p, y): ({pose.roll:+.2f}°, {pose.pitch:+.2f}°, {pose.yaw:+.2f}°)")
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
        print("[Camera] Camera stopped.")


def main():
    global running
    
    ap = argparse.ArgumentParser(description="PlantHopper: AprilTag detection with Firebase and Arduino control")
    ap.add_argument("--cam", type=int, default=0, help="Camera index (default 0)")
    ap.add_argument("--width", type=int, default=1280, help="Capture width")
    ap.add_argument("--height", type=int, default=720, help="Capture height")
    ap.add_argument("--dict", type=str, default="DICT_APRILTAG_36h11",
                    help="Tag dictionary (e.g., DICT_APRILTAG_36h11, DICT_APRILTAG_25h9)")
    ap.add_argument("--tag-size", type=float, default=0.072,
                    help="Tag size in meters (edge length)")
    ap.add_argument("--calib", type=str, default="./Firebase/logitech_config.yaml",
                    help="Path to camera calibration file")
    ap.add_argument("--firebase-cred", type=str, 
                    default="./Firebase/planthopper-2fbc8-firebase-adminsdk-fbsvc-bf21b9e16e.json",
                    help="Path to Firebase credentials JSON")
    ap.add_argument("--arduino-port", type=str, default="/dev/tty.usbserial-A50285BI",
                    help="Arduino serial port")
    ap.add_argument("--sweep-duration", type=float, default=2.0,
                    help="Duration of sweep operation in seconds")
    args = ap.parse_args()

    print("="*60)
    print("PlantHopper System Starting")
    print("="*60)
    print("Press Q in the camera window or Ctrl+C to stop.\n")

    # Define plant-to-AprilTag mapping
    # This maps Firebase plant IDs to their corresponding AprilTag IDs
    plant_tag_mapping = {
        "plant1": 1,
        "plant2": 2,
        "plant3": 3,
        "plant4": 4,
        "plant5": 5,
        # Add more mappings as needed
    }

    try:
        # Initialize Arduino controller
        arduino = ArduinoController(port=args.arduino_port)
        
        # Initialize AprilTag detector
        detector = AprilTagDetector(
            calib_path=args.calib,
            tag_size=args.tag_size,
            dict_name=args.dict
        )
        
        # Initialize shooting system
        shooting_system = ShootingSystem(
            arduino=arduino,
            detector=detector,
            sweep_duration=args.sweep_duration
        )
        
        # Initialize camera
        cap = cv2.VideoCapture(args.cam)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {args.cam}")
        
        print("[Main] All systems initialized successfully\n")
        
        # Start Firebase listener in background thread
        fb_thread = threading.Thread(
            target=firebase_thread,
            args=(args.firebase_cred, shooting_system, cap, plant_tag_mapping),
            daemon=True
        )
        fb_thread.start()
        
        # Give Firebase thread a moment to initialize
        time.sleep(1)

        # Run camera in main thread (required for OpenCV GUI)
        run_camera(args, shooting_system, cap)
    
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt detected. Stopping...")
        running = False
    
    except Exception as e:
        print(f"[Main] Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        running = False
    
    finally:
        # Cleanup
        print("\n[Main] Shutting down...")
        running = False
        
        # Wait for Firebase thread to finish
        if 'fb_thread' in locals():
            print("[Main] Waiting for Firebase thread to stop...")
            fb_thread.join(timeout=2)
        
        # Release camera
        if 'cap' in locals():
            cap.release()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        # Close Arduino connection
        if 'arduino' in locals():
            arduino.close()
        
        print("[Main] Program terminated.")
        print("="*60)


if __name__ == "__main__":
    main()