import os
import requests
from urllib.parse import urlencode
from ..config import settings

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_AUTH_URL   = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL  = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url():
    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  settings.google_redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "consent",
    }
    # urlencode — bo'shliq va maxsus belgilarni to'g'ri encode qiladi
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def get_google_user_info(code: str):
    # 1. Code → Token
    token_res = requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri":  settings.google_redirect_uri,
        "grant_type":    "authorization_code",
    })

    if not token_res.ok:
        return None

    token_data   = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return None

    # 2. Token → User info
    user_res = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not user_res.ok:
        return None

    return user_res.json()