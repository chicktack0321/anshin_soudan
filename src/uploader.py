"""YouTube Data API v3 による自動投稿"""
from pathlib import Path

from .config import ROOT, DATA_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = DATA_DIR / "youtube_token.json"


def _get_service(cfg: dict):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    secrets = ROOT / cfg["youtube"]["client_secrets"]
    if not secrets.exists():
        raise SystemExit(
            f"OAuthクレデンシャルがありません: {secrets}\n"
            "Google Cloud Console で YouTube Data API v3 を有効化し、\n"
            "OAuthクライアントID(デスクトップアプリ)を作成して client_secrets.json を配置してください。"
        )

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path, title: str, description: str, tags: list[str], cfg: dict
) -> str:
    """動画をアップロードして YouTube 動画IDを返す"""
    from googleapiclient.http import MediaFileUpload

    service = _get_service(cfg)
    yc = cfg["youtube"]

    if "#Shorts" not in title and "#shorts" not in description:
        description = description.rstrip() + "\n#Shorts"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": (tags + yc.get("default_tags", []))[:30],
            "categoryId": yc.get("category_id", "27"),
            "defaultLanguage": "ja",
        },
        "status": {
            "privacyStatus": yc.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  アップロード中... {int(status.progress() * 100)}%")
    return response["id"]
