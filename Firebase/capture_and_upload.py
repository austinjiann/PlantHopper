#!/usr/bin/env python3
import argparse
import io
import os
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

import cv2  # type: ignore
from dotenv import load_dotenv  # type: ignore

import firebase_admin  # type: ignore
from firebase_admin import credentials, storage, firestore


def read_env() -> dict:
    # Load .env from project root (one level up from Firebase/ directory)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    
    config = {
        "service_account": os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "storage_bucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    }
    required = ["service_account", "project_id", "storage_bucket"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return config


def init_firebase(config: dict):
    if not firebase_admin._apps:
        cred = credentials.Certificate(config["service_account"])
        firebase_admin.initialize_app(cred, {
            "projectId": config["project_id"],
            "storageBucket": config["storage_bucket"],
        })
    return firestore.client(), storage.bucket()


def capture_frame(camera_index: int, preview: bool) -> tuple[bool, any]:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {camera_index}")

    ret, frame = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError("Failed to read frame from camera")

    if preview:
        win = "Press space to capture, q to quit"
        cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow(win, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (32, 13):  # space or enter
                break
            if key in (27, ord('q')):
                cap.release()
                cv2.destroyAllWindows()
                raise SystemExit("Cancelled by user")
        cv2.destroyAllWindows()

    cap.release()
    return True, frame


def encode_jpeg(frame) -> bytes:
    ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buf.tobytes()


def upload_to_storage(bucket, data: bytes, plant_id: str, label: str | None):
    ts = datetime.now(timezone.utc)
    timestamp_str = ts.strftime('%Y%m%dT%H%M%SZ')
    path = f"images/{plant_id}/{timestamp_str}.jpg"
    blob = bucket.blob(path)

    token = str(uuid4())
    blob.metadata = {"firebaseStorageDownloadTokens": token}
    blob.upload_from_file(io.BytesIO(data), content_type="image/jpeg")

    # Public download URL format for token-based access
    url = (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
        f"{path.replace('/', '%2F')}?alt=media&token={token}"
    )
    return path, url, ts


def write_firestore(db, plant_id: str, storage_path: str, url: str, ts: datetime, width: int, height: int, label: str | None):
    doc = {
        "plantId": plant_id,
        "storagePath": storage_path,
        "downloadURL": url,
        "timestamp": ts,
        "width": width,
        "height": height,
    }
    if label:
        doc["label"] = label
    db.collection("plant_images").add(doc)




def main():
    parser = argparse.ArgumentParser(description="Capture an image from webcam and upload to Firebase")
    parser.add_argument("--plant-id", required=True, help="Plant id (e.g., plant1)")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0)")
    parser.add_argument("--no-preview", action="store_true", help="Capture without preview window")
    parser.add_argument("--label", default=None, help="Optional label for the image")
    args = parser.parse_args()

    cfg = read_env()
    db, bucket = init_firebase(cfg)

    success, frame = capture_frame(args.camera, not args.no_preview)
    height, width = frame.shape[:2]
    data = encode_jpeg(frame)

    storage_path, url, ts = upload_to_storage(bucket, data, args.plant_id, args.label)
    write_firestore(db, args.plant_id, storage_path, url, ts, width, height, args.label)

    print("Uploaded:", storage_path)
    print("URL:", url)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)

