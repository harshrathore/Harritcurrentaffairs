import os
import sys
import time
import json
import webbrowser
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(BASE, "..", "data", "PIB", "slides")
UPLOAD_LOG = os.path.join(BASE, "uploaded_files.json")
MASTER_FILE = os.path.join(SLIDES_DIR, "current_affairs_all.pptx")
TOKEN_FILE = os.path.join(BASE, "token.json")
CREDENTIALS_FILE = os.path.join(BASE, "credentials.json")


def check_internet():
    import requests
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


def is_gdrive_authenticated():
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, ["https://www.googleapis.com/auth/drive.file"])
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(requests.Request())
        return creds and creds.valid
    except Exception:
        return False


def setup_gdrive_auth():
    print("=" * 50)
    print("GOOGLE DRIVE SETUP REQUIRED")
    print("=" * 50)
    print()
    print("Steps:")
    print("1. A browser window will open")
    print("2. Sign in with your Google account")
    print("3. Allow access to Google Drive")
    print("4. Come back here after allowing")
    print()
    input("Press Enter to open browser...")
    
    try:
        from google_drive_upload import get_credentials
        creds = get_credentials()
        if creds:
            print()
            print("SUCCESS! Google Drive authenticated.")
            print("Auto-upload will now work.")
            return True
        else:
            print("Authentication failed. Try again later.")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def load_uploaded():
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_uploaded(data):
    with open(UPLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def upload_new_files():
    if not os.path.exists(MASTER_FILE):
        return False

    uploaded = load_uploaded()
    mtime = os.path.getmtime(MASTER_FILE)
    mtime_str = str(mtime)

    if mtime_str in uploaded:
        return False

    try:
        from google_drive_upload import upload_to_drive
        result = upload_to_drive(MASTER_FILE)
        if result["success"]:
            uploaded[mtime_str] = {
                "uploaded_at": datetime.now().isoformat(),
                "link": result["link"]
            }
            save_uploaded(uploaded)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Uploaded: {result['link']}")
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Upload failed: {result['message']}")
            return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        return False


def watch_loop():
    print("=" * 50)
    print("GOOGLE DRIVE AUTO-UPLOADER")
    print("=" * 50)
    print()
    print("Waiting for internet connection...")
    
    while not check_internet():
        time.sleep(10)
    
    print("Internet connected!")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print("ERROR: credentials.json not found")
        print("Please set up Google Cloud first.")
        input("Press Enter to exit...")
        return
    
    if not is_gdrive_authenticated():
        print("Google Drive not authenticated.")
        if not setup_gdrive_auth():
            input("Press Enter to exit...")
            return
    
    print()
    print("Monitoring for new slides...")
    print(f"Directory: {SLIDES_DIR}")
    print("Checking every 60 seconds...")
    print()
    
    while True:
        try:
            if check_internet():
                upload_new_files()
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No internet, waiting...")
                while not check_internet():
                    time.sleep(10)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Internet restored!")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)


if __name__ == "__main__":
    watch_loop()
