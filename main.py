import os
import json
import datetime as dt
from typing import Optional

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


# ----------------------------
# Toggl (Reports API v3) fetch
# ----------------------------
def fetch_toggl_csv(
    workspace_id: str,
    toggl_api_token: str,
    start_date: str,
    end_date: str,
) -> bytes:
    """
    Fetch time entries as CSV from Toggl Reports API v3.

    Endpoint:
      POST https://api.track.toggl.com/reports/api/v3/workspace/{workspace_id}/search/time_entries.csv

    Notes:
      - This endpoint expects POST (GETだと 405 Method Not Allowed になりやすい)
      - start_date/end_date は JSON body で渡す
    """
    url = f"https://api.track.toggl.com/reports/api/v3/workspace/{workspace_id}/search/time_entries.csv"

    headers = {
        "Accept": "text/csv",
        "Content-Type": "application/json",
    }

    payload = {
        "start_date": start_date,
        "end_date": end_date,
        # 必要になったら以下を追加できます（例）:
        # "user_ids": [12345],
        # "project_ids": [111, 222],
        # "client_ids": [333],
        # "billable": True,
        # "description": "keyword",
    }

    r = requests.post(
        url,
        headers=headers,
        json=payload,
        auth=(toggl_api_token, "api_token"),
        timeout=60,
    )
    r.raise_for_status()
    return r.content


# ----------------------------
# Google Drive (OAuth) upload
# ----------------------------
def get_drive_service_from_token_json(token_json_str: str):
    """
    token_json_str: creds.to_json() の出力をそのまま入れる（GOOGLE_DRIVE_TOKEN）
    """
    info = json.loads(token_json_str)
    creds = Credentials.from_authorized_user_info(info)

    # 期限切れなら refresh_token で更新
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("drive", "v3", credentials=creds)


def upload_bytes_to_drive(
    drive_service,
    file_bytes: bytes,
    filename: str,
    mime_type: str = "text/csv",
    folder_id: Optional[str] = None,
) -> dict:
    """
    Upload in-memory bytes to Google Drive.
    folder_id を指定すると、そのフォルダ配下に置く。
    """
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaInMemoryUpload(file_bytes, mimetype=mime_type, resumable=False)

    created = (
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink",
        )
        .execute()
    )
    return created


# ----------------------------
# Helpers
# ----------------------------
def iso_date(d: dt.date) -> str:
    return d.strftime("%Y-%m-%d")


def default_date_range(days: int = 90):
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    return iso_date(start), iso_date(end)


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def main():
    # --- Required ---
    toggl_api_token = require_env("TOGGL_API_TOKEN")
    workspace_id = require_env("TOGGL_WORKSPACE_ID")
    drive_token_json = require_env("GOOGLE_DRIVE_TOKEN")

    # --- Optional ---
    folder_id = os.environ.get("DRIVE_FOLDER_ID")  # なくても My Drive 直下に保存されます
    start_date = os.environ.get("START_DATE")
    end_date = os.environ.get("END_DATE")

    if not start_date or not end_date:
        start_date, end_date = default_date_range(days=90)

    # 1) Fetch CSV from Toggl
    csv_bytes = fetch_toggl_csv(
        workspace_id=workspace_id,
        toggl_api_token=toggl_api_token,
        start_date=start_date,
        end_date=end_date,
    )

    # 2) Upload to Google Drive (OAuth)
    drive = get_drive_service_from_token_json(drive_token_json)

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"toggl_time_entries_{start_date}_to_{end_date}_{timestamp}.csv"

    created = upload_bytes_to_drive(
        drive_service=drive,
        file_bytes=csv_bytes,
        filename=filename,
        mime_type="text/csv",
        folder_id=folder_id,
    )

    print("✅ Upload complete")
    print(f"File: {created.get('name')}")
    print(f"ID: {created.get('id')}")
    print(f"Link: {created.get('webViewLink')}")


if __name__ == "__main__":
    main()
