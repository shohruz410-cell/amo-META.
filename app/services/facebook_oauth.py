import secrets
import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from app.models.database import db
from app.models.facebook import FacebookOAuth

load_dotenv()

APP_ID = os.getenv("FB_APP_ID")
APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = os.getenv("FB_REDIRECT_URI")

def exchange_code_for_token(code: str) -> dict:
    """Short-lived token olish"""
    url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def exchange_for_long_lived_token(short_token: str) -> dict:
    """Short-lived → Long-lived token (60 kun)"""
    url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def get_business_id(access_token: str) -> int:
    """Foydalanuvchi business_id larini olish"""
    url = "https://graph.facebook.com/v19.0/me/businesses"
    params = {"access_token": access_token}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise Exception("Business topilmadi")
    return int(data[0]["id"])

def save_pending(access_token: str, business_id: int, expires_in: int) -> FacebookOAuth:
    """Callback dan keyin vaqtinchalik saqlash — pending_token qaytaradi"""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    pending_token = secrets.token_hex(32)

    existing = FacebookOAuth.query.filter_by(business_id=business_id).first()
    if existing:
        existing.access_token = access_token
        existing.expires_at = expires_at
        existing.pending_token = pending_token
    else:
        existing = FacebookOAuth(
            business_id=business_id,
            access_token=access_token,
            refresh_token="",
            expires_at=expires_at,
            pending_token=pending_token,
        )
        db.session.add(existing)

    db.session.commit()
    return existing


def complete_save(pending_token: str, ad_account_id: int, pixel_id: int) -> FacebookOAuth:
    """ad_account_id va pixel_id ni qo'shib saqlashni yakunlash"""
    record = FacebookOAuth.query.filter_by(pending_token=pending_token).first()
    if not record:
        raise ValueError("pending_token topilmadi yoki eskirgan")

    record.ad_account_id = ad_account_id
    record.pixel_id = pixel_id
    record.pending_token = None
    db.session.commit()
    return record