#!/usr/bin/env python3
import argparse
import io
import os
import sys
import time
import json
import re
import random
from datetime import datetime, timezone
from uuid import uuid4

import cv2  # type: ignore
from dotenv import load_dotenv  # type: ignore

import firebase_admin  # type: ignore
from firebase_admin import credentials, storage, firestore

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - optional at import time
    genai = None

def read_env() -> dict:
    # Load .env from project root (one level up from Firebase/ directory)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    
    config = {
        "service_account": os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "storage_bucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
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


def _extract_json(text: str) -> dict:
    """Attempt to extract a JSON object from free-form model text.

    Handles cases where the response is wrapped in code fences or contains prose.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove code fences if present
    fenced = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text.strip())
    try:
        return json.loads(fenced)
    except Exception:
        pass

    # Greedy find the first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    raise ValueError("Model did not return valid JSON")


def analyze_with_gemini(image_bytes: bytes, api_key: str, max_retries: int = 3) -> dict:
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")
    if genai is None:
        raise RuntimeError("google-generativeai is not installed. Run: pip install google-generativeai")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = (
        "You are an image analyst. Always return a SINGLE JSON object only. "
        "Identify plant species if possible and provide a reasonable target soil moisture percentage (0-100). "
        "If the image is NOT a plant or you are unsure, set isPlant=false and still provide a fabricated but plausible targetMoisture (e.g., 30-70) and reason. "
        "Keys: isPlant(bool), inPot(bool or null), species{common,scientific,confidence:int}, targetMoisture:int, reason:string. "
        "Do not include any text outside JSON."
    )

    last_error = None
    for _ in range(max_retries):
        try:
            resp = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": image_bytes},
            ])
            text = getattr(resp, "text", None)
            if not text and hasattr(resp, "candidates") and resp.candidates:
                # Fallback: concatenate parts
                parts = []
                for c in resp.candidates:
                    for p in getattr(getattr(c, "content", None), "parts", []) or []:
                        val = getattr(p, "text", None)
                        if val:
                            parts.append(val)
                text = "\n".join(parts)
            if not text:
                raise ValueError("Empty response from model")
            return _extract_json(text)
        except Exception as e:  # keep retrying on parse/network errors
            last_error = e
            time.sleep(1.0)
    # If all retries failed, return a conservative default
    raise RuntimeError(f"Gemini analysis failed: {last_error}")


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


def write_firestore(db, plant_id: str, storage_path: str, url: str, ts: datetime, width: int, height: int, label: str | None, analysis: dict | None):
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
    if analysis:
        # Persist only well-formed fields
        species = analysis.get("species") or {}
        if isinstance(species, dict):
            doc["species"] = {
                k: species.get(k) for k in ("common", "scientific", "confidence") if species.get(k) is not None
            }
        tm = analysis.get("targetMoisture")
        if isinstance(tm, (int, float)) and 0 <= float(tm) <= 100:
            doc["targetMoisture"] = int(round(float(tm)))
        reason = analysis.get("reason")
        if isinstance(reason, str) and reason:
            doc["aiAnalysis"] = reason
        # Also store booleans for debugging/filters
        for k in ("isPlant", "inPot"):
            v = analysis.get(k)
            if isinstance(v, bool):
                doc[k] = v
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

    # Single capture, always proceed
    success, frame = capture_frame(args.camera, not args.no_preview)
    height, width = frame.shape[:2]
    data = encode_jpeg(frame)

    analysis: dict | None = None
    try:
        analysis = analyze_with_gemini(data, cfg.get("gemini_api_key"))
    except Exception as e:
        print(f"[Gemini] analysis failed: {e}. Using fallback random values.")
        analysis = {}

    # If not a plant or fields missing, fabricate reasonable defaults
    if not isinstance(analysis, dict):
        analysis = {}
    species = analysis.get("species") or {}
    if not isinstance(species, dict):
        species = {}
    analysis.setdefault("isPlant", bool(species.get("common")))
    analysis.setdefault("inPot", None)
    species.setdefault("common", species.get("common") or "Unknown")
    species.setdefault("scientific", species.get("scientific") or None)
    species.setdefault("confidence", int(species.get("confidence") or 0))
    analysis["species"] = species
    tm = analysis.get("targetMoisture")
    if not isinstance(tm, (int, float)):
        analysis["targetMoisture"] = random.randint(30, 70)
    analysis.setdefault("reason", analysis.get("reason") or "Fallback values generated for non-plant or low confidence image")

    storage_path, url, ts = upload_to_storage(bucket, data, args.plant_id, args.label)
    write_firestore(db, args.plant_id, storage_path, url, ts, width, height, args.label, analysis)

    print("Uploaded:", storage_path)
    print("URL:", url)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)

