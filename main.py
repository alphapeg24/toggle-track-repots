import os
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.auth import default


def main():
    folder_id = os.environ["DRIVE_FOLDER_ID"]

    creds, _ = default(scopes=["https://www.googleapis.com/auth/drive.file"])
    drive = build("drive", "v3", credentials=creds)

    content = f"Hello from GitHub Actions!\n{datetime.now().isoformat()}\n".encode("utf-8")
    media = MediaInMemoryUpload(content, mimetype="text/plain")

    file_metadata = {
        "name": "gh-actions-test.txt",
        "parents": [folder_id],
    }

    created = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()

    print("Uploaded:", created["name"])
    print("File ID:", created["id"])
    print("Link:", created.get("webViewLink"))


if __name__ == "__main__":
    main()
