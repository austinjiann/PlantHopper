import firebase_admin
from firebase_admin import credentials, firestore
import time

cred = credentials.Certificate("./Firebase/planthopper-2fbc8-firebase-adminsdk-fbsvc-bf21b9e16e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        data = doc.to_dict()
        if data.get("command") == "water":
            print(f"Watering {doc.id}!")
            # send serial command to Arduino
            # reset command
            db.collection("plants").document(doc.id).update({
                "command": None,
                "lastWatered": firestore.SERVER_TIMESTAMP
            })

doc_ref = db.collection("plants").document("plant1")
doc_watch = doc_ref.on_snapshot(on_snapshot)

# Keep the script running
try:
    print("Listening for changes... Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping listener...")
    doc_watch.unsubscribe()