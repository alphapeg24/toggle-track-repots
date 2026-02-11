import os
import json
import base64
from datetime import datetime, timedelta, timezone

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


def toggl_auth_header(api_token: str) -> str:
    raw = f"{api_token}:api_token".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def fetch_toggl_csv(workspace_id: str, api_token: str, start_date: str, end_date: str) -> bytes:
    # Toggl Reports API (CSV export)
    url = f"https://api.track.toggl.com/reports/api/v3/workspace/{workspace_id}/search/time_entries.csv"
    headers = {
        "Authorization": toggl_auth_header(api_token),
    }
    params = {
        "start_date": start_date,  # YYYY-MM-DD
        "end_date": end_date,      # YYYY-MM-DD
    }
    r = requests.get(url, headers=headers, params=params, timeout=60)
    r.raise_for_status()
    return r.content


def drive_client_from_token(token_json: str):
    creds = Credentials.from_authorized_user_info(json.loads(token_json))
    return build("drive", "v3", credentials=creds)


def upload_bytes_to_drive(drive, folder_id: str, filename: str, content: bytes, mimetype: str):
    media = MediaInMemoryUpload(content, mimetype=mimetype)
    body = {"name": filename, "parents": [folder_id]}
    created = drive.files().create(body=body, media_body=media, fields="id,name,webViewLink").execute()
    return created


def main():
    # Secrets / env
    toggl_token = os.environ["TOGGL_API_TOKEN"]
    workspace_id = os.environ["TOGGL_WORKSPACE_ID"]
    folder_id = os.environ["DRIVE_FOLDER_ID"]
    drive_token = os.environ["GOOGLE_DRIVE_TOKEN"]

    # Date range: last 90 days (JST)
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).date()
    start = (today - timedelta(days=90)).isoformat()
    end = today.isoformat()

    # Fetch CSV
    csv_bytes = fetch_toggl_csv(workspace_id, toggl_token, start, end)

    # Upload to Drive
    drive = drive_client_from_token(drive_token)
    filename = f"toggl_time_entries_{start}_to_{end}.csv"
    created = upload_bytes_to_drive(drive, folder_id, filename, csv_bytes, "text/csv")

    print("Uploaded:", created["name"])
    print("Link:", created.get("webViewLink"))


if __name__ == "__main__":
    main()
