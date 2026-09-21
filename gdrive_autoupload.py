import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(BASE, "..", "data", "PIB", "slides")
UPLOAD_LOG = os.path.join(BASE, "uploaded_files.json")
MASTER_FILE = os.path.join(SLIDES_DIR, "current_affairs_all.pptx")


def load_uploaded():
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_uploaded(data):
    with open(UPLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def check_internet():
    import requests
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


def upload_new_files():
    if not check_internet():
        print("No internet connection")
        return

    if not os.path.exists(MASTER_FILE):
        print("No master file found")
        return

    uploaded = load_uploaded()
    mtime = os.path.getmtime(MASTER_FILE)
    mtime_str = str(mtime)

    if mtime_str in uploaded:
        print("No new slides to upload")
        return

    print("New slides found, uploading to Google Drive...")
    try:
        from google_drive_upload import upload_to_drive
        result = upload_to_drive(MASTER_FILE)
        if result["success"]:
            uploaded[mtime_str] = {
                "uploaded_at": datetime.now().isoformat(),
                "link": result["link"]
            }
            save_uploaded(uploaded)
            print(f"Uploaded: {result['link']}")
        else:
            print(f"Upload failed: {result['message']}")
    except Exception as e:
        print(f"Error: {e}")


def watch_loop():
    print("Google Drive auto-uploader started")
    print(f"Watching: {SLIDES_DIR}")
    while True:
        try:
            upload_new_files()
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        upload_new_files()
    else:
        watch_loop()
