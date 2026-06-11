"""
youtube_uploader.py
Uploads a video file to YouTube using the YouTube Data API v3.

Local run: opens a browser for OAuth consent → saves token.pickle.
GitHub Actions run: uses base64 secrets from environment variables.
"""

import os
import pickle
import base64

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.editor import VideoFileClip 

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS = "client_secrets.json"   # Used for local execution

def extract_thumbnail(video_path: str) -> str:
    """Grabs a frame at t=0.5s — question visible, answer not yet shown."""
    thumb_path = video_path.replace(".mp4", "_thumb.jpg")
    clip = VideoFileClip(video_path)
    clip.save_frame(thumb_path, t=0.5)
    clip.close()
    return thumb_path


def _set_thumbnail(youtube, video_id: str, thumb_path: str):
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumb_path, mimetype="image/jpeg"),
        ).execute()
        print("🖼️  Thumbnail set.")
    except Exception as e:
        print(f"⚠️  Thumbnail upload failed (channel verified?): {e}")
    finally:
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

def _get_service():
    creds = None

    # --- 1. ENVIRONMENT / GITHUB ACTIONS CREDENTIAL FLOW ---
    if os.environ.get("GOOGLE_TOKEN_BASE64") and os.environ.get("GOOGLE_CREDENTIALS_BASE64"):
        print("🤖 Running in CI/CD environment (GitHub Actions)...")
        
        # Write temporary credentials.json from secret
        creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
        with open("credentials.json", "wb") as f:
            f.write(base64.b64decode(creds_b64))

        # Reconstruct credentials object from base64 token secret
        token_b64 = os.environ.get("GOOGLE_TOKEN_BASE64")
        token_bytes = base64.b64decode(token_b64)
        creds = pickle.loads(token_bytes)

        # Refresh token if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Note: If the token refreshes in GitHub Actions, you may occasionally need
            # to capture the print statement from logs and update your secret.
            # updated_b64 = base64.b64encode(pickle.dumps(creds)).decode('utf-8')
            # print(f"UPDATED REFRESHED TOKEN: {updated_b64}")
            
    # --- 2. LOCAL ENVIRONMENT CREDENTIAL FLOW ---
    else:
        print("💻 Running in local development environment...")
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        # If local token is missing or expired, prompt browser login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS):
                    raise FileNotFoundError(
                        f"Missing {CLIENT_SECRETS}. "
                        "Download it from Google Cloud Console → APIs & Services → Credentials."
                    )
                # Lock port to 8080 to prevent redirect_uri_mismatch errors
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
                creds = flow.run_local_server(port=8080)

            # Cache the token locally for future local runs
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

    # Clean up temporary file if it was created during CI/CD execution
    if os.path.exists("credentials.json"):
        os.remove("credentials.json")

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
            "title":       title[:100],   # YouTube max title length constraint
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

    request = youtube.videos().insert(
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
    print(f"\n✅ Uploaded → https://youtube.com/watch?v={video_id}")
    # Set thumbnail — question only, answer hidden
    thumb_path = extract_thumbnail(video_path)
    _set_thumbnail(youtube, video_id, thumb_path)

    return video_id
