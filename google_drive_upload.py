import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE, "credentials.json")
TOKEN_FILE = os.path.join(BASE, "token.json")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print("ERROR: credentials.json not found")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def upload_to_drive(filepath, folder_id=None):
    creds = get_credentials()
    if not creds:
        return {"success": False, "message": "Auth failed"}

    service = build("drive", "v3", credentials=creds)
    filename = os.path.basename(filepath)

    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(filepath, resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    file_id = file.get("id")
    link = file.get("webViewLink")

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()

    print(f"Uploaded: {filename}")
    print(f"Link: {link}")
    return {"success": True, "file_id": file_id, "link": link}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: py google_drive_upload.py <filepath> [folder_id]")
        sys.exit(1)
    filepath = sys.argv[1]
    folder_id = sys.argv[2] if len(sys.argv) > 2 else None
    upload_to_drive(filepath, folder_id)
