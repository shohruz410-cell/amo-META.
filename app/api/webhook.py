import os
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from app.models.amo import AmoOAuth
from app.models.database import db
from senzib_amo.client import AmoCRMClient
from senzib_amo.oauth.tokens import AccessToken

webhook_bp = Blueprint("webhook", __name__)

CLIENT_ID = os.getenv("AMO_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AMO_REDIRECT_URI")


def _get_phone(custom_fields_values):
    if not custom_fields_values:
        return None
    for cf in custom_fields_values:
        if cf.get("field_code") == "PHONE":
            values = cf.get("values", [])
            if values:
                return values[0].get("value")
    return None


def _build_client(oauth: AmoOAuth) -> AmoCRMClient:
    token = AccessToken(
        access_token=oauth.access_token,
        refresh_token=oauth.refresh_token,
    )

    client = AmoCRMClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        base_domain=f"{oauth.subdomain}.amocrm.ru",
    )
    client.set_access_token(token)

    def on_token_refresh(new_token: AccessToken, base_domain: str) -> None:
        oauth.access_token = new_token.access_token
        oauth.refresh_token = new_token.refresh_token
        if new_token.expires_at:
            oauth.expires_at = datetime.fromtimestamp(new_token.expires_at, tz=timezone.utc)
        db.session.commit()

    client.set_access_token_refresh_callback(on_token_refresh)
    return client


@webhook_bp.route("/amo/webhook", methods=["POST"])
def amo_webhook():
    data = request.form

    lead_id = data.get("leads[status][0][id]")
    price_raw = data.get("leads[status][0][price]")
    account_id = data.get("account[id]")

    if not lead_id or not account_id:
        return jsonify({"error": "leads[status][0][id] yoki account[id] yo'q"}), 400

    oauth = AmoOAuth.query.filter_by(account_id=int(account_id)).first()
    if not oauth:
        return jsonify({"error": f"account_id={account_id} uchun token topilmadi"}), 404

    client = _build_client(oauth)

    lead = client.leads.get_one(int(lead_id), params={"with": "contacts"})

    client_name = None
    client_phone = None

    contacts = lead._embedded.get("contacts", [])
    if contacts:
        contact_id = contacts[0].get("id")
        if contact_id:
            contact = client.contacts.get_one(
                contact_id, params={"with": "custom_fields_values"}
            )
            client_name = contact.name
            client_phone = _get_phone(contact.custom_fields_values)

    return jsonify({
        "amocrm_lead_id": int(lead_id),
        "client_name": client_name,
        "client_phone": client_phone,
        "price": int(price_raw) if price_raw else lead.price,
    }), 200
