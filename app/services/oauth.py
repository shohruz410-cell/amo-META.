
import os

from dotenv import load_dotenv
from flask import Blueprint, redirect, request, jsonify, session

from app.services.amo_oauth import exchange_code_for_tokens, save_tokens as save_amo_tokens
from app.services.facebook_oauth import (
    exchange_code_for_token,
    exchange_for_long_lived_token,
    get_business_id,
    save_pending as facebook_save_pending,
    complete_save as facebook_complete_save,
)

load_dotenv()

AMO_CLIENT_ID = os.getenv("AMO_CLIENT_ID")
AMO_REDIRECT_URI = os.getenv("AMO_REDIRECT_URI")

oauth_bp = Blueprint("oauth", __name__)


@oauth_bp.route("/oauth/authorize")
def authorize():
    """Foydalanuvchini AmoCRM ga yo'naltirish"""
    raw_subdomain = request.args.get("subdomain", "")

    # Extract only the subdomain part if user accidentally sent full URL
    subdomain = raw_subdomain.replace("https://", "").replace("http://", "").split(".amocrm.ru")[0].strip("/")

    url = (
        f"https://www.amocrm.ru/oauth?"
        f"client_id={AMO_CLIENT_ID}"
        f"&redirect_uri={AMO_REDIRECT_URI}"
        f"&response_type=code"
        f"&state={subdomain}"
    )
    return redirect(url)


@oauth_bp.route("/callback")
def callback():
    """AmoCRM qaytargan code ni qabul qilish"""
    code = request.args.get("code")
    subdomain = request.args.get("state")  # state orqali subdomain yuborilgan

    if not code or not subdomain:
        return jsonify({"error": "code yoki subdomain yo'q"}), 400

    try:
        token_data = exchange_code_for_tokens(code, subdomain)
        oauth = save_amo_tokens(token_data, subdomain)
        return jsonify({
            "message": "Muvaffaqiyatli saqlandi",
            "account_id": oauth.account_id,
            "subdomain": oauth.subdomain,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500




fb_bp = Blueprint("fb_oauth", __name__)

FB_APP_ID = os.getenv("FB_APP_ID")
FB_REDIRECT_URI = os.getenv("FB_REDIRECT_URI")

SCOPES = "business_management,ads_management,ads_read"


@fb_bp.route("/facebook/authorize")
def authorize():
    url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={FB_APP_ID}"
        f"&redirect_uri={FB_REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&response_type=code"
    )
    return redirect(url)


@fb_bp.route("/facebook/callback")
def callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return jsonify({"error": request.args.get("error_description")}), 400

    if not code:
        return jsonify({"error": "code yo'q"}), 400

    try:
        # 1. Short-lived token
        token_data = exchange_code_for_token(code)
        short_token = token_data["access_token"]

        # 2. Long-lived token (60 kun)
        long_data = exchange_for_long_lived_token(short_token)
        access_token = long_data["access_token"]
        expires_in = long_data.get("expires_in", 5184000)  # 60 kun default

        # 3. Business ID
        business_id = get_business_id(access_token)

        record = facebook_save_pending(access_token, business_id, expires_in)

        return jsonify({
            "message": "Token olindi",
            "business_id": business_id,
            "pending_token": record.pending_token,
            "next_step": "pending_token, ad_account_id va pixel_id ni yuboring",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fb_bp.route("/facebook/save", methods=["POST"])
def save():
    """pending_token, ad_account_id va pixel_id ni qabul qilib saqlashni yakunlaydi"""
    data = request.json or {}
    missing = [k for k in ("pending_token", "ad_account_id", "pixel_id") if k not in data]
    if missing:
        return jsonify({"error": f"Maydonlar yetishmayapti: {', '.join(missing)}"}), 400

    try:
        oauth = facebook_complete_save(
            pending_token=data["pending_token"],
            ad_account_id=data["ad_account_id"],
            pixel_id=data["pixel_id"],
        )
        return jsonify({"message": "Saqlandi", "id": oauth.id})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
