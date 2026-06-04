"""
youtube_uploader.py
Uploads a video file to YouTube using the YouTube Data API v3.

First run: opens a browser for OAuth consent → saves token.pickle.
Subsequent runs: uses the saved token (auto-refreshed).
"""

import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS = "client_secrets.json"   # download from Google Cloud Console


def _get_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS):
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRETS}. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow  = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: str, title: str, description: str,
                 tags: list | None = None) -> str:
    """
    Upload video_path to YouTube.
    Returns the YouTube video ID on success.
    """
    youtube = _get_service()

    body = {
        "snippet": {
            "title":       title[:100],   # YouTube max title length
            "description": description,
            "tags":        tags or ["puns", "dadjokes", "funny", "shorts", "comedy"],
            "categoryId":  "23",          # Comedy
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,   # 4 MB chunks
    )

    request  = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Uploading… {pct}%", end="\r")

    video_id = response["id"]
    print(f"✅  Uploaded → https://youtube.com/watch?v={video_id}")
    return video_id
