import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from app.models.amo import AmoOAuth
from app.models.database import db

load_dotenv()

CLIENT_ID = os.getenv("AMO_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AMO_REDIRECT_URI")


def exchange_code_for_tokens(code: str, subdomain: str) -> dict:
    """Authorization code → access/refresh token olish"""
    url = f"https://{subdomain}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def save_tokens(data: dict, subdomain: str) -> AmoOAuth:
    """Tokenlarni bazaga saqlash yoki yangilash"""
    account_id = data["account_id"] if "account_id" in data else get_account_id(data["access_token"], subdomain)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

    existing = AmoOAuth.query.filter_by(account_id=account_id).first()

    if existing:
        existing.access_token = data["access_token"]

        existing.refresh_token = data["refresh_token"]
        existing.expires_at = expires_at
        existing.subdomain = subdomain
    else:
        existing = AmoOAuth(
            account_id=account_id,
            subdomain=subdomain,
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=expires_at,
        )
        db.session.add(existing)

    db.session.commit()
    return existing


def get_account_id(access_token: str, subdomain: str) -> int:
    """AmoCRM dan account_id olish"""
    url = f"https://{subdomain}.amocrm.ru/api/v4/account"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def refresh_access_token(oauth: AmoOAuth) -> AmoOAuth:
    """Refresh token orqali yangi access token olish"""
    url = f"https://{oauth.subdomain}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": oauth.refresh_token,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()

    oauth.access_token = data["access_token"]
    oauth.refresh_token = data["refresh_token"]
    oauth.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
    db.session.commit()
    return oauth
