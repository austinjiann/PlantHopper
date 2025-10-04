import cv2

def find_cameras(max_index=10):
    print("Scanning for available cameras...")
    available = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"✅ Camera found at index {i}")
            available.append(i)
            cap.release()
        else:
            print(f"❌ No camera at index {i}")
    return available

if __name__ == "__main__":
    cams = find_cameras()
    if not cams:
        print("No working cameras found.")
    else:
        print(f"Available camera indices: {cams}")
