import secrets

from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.settings import get_settings
from app.db.store import store

settings = get_settings()
serializer = URLSafeTimedSerializer(
    settings.session_secret or secrets.token_urlsafe(48), salt="repolens-session-v1"
)


def owner(request: Request) -> str:
    return request.state.owner_id


def authorized(table: str, identifier: str, user: str) -> dict:
    record = store.get(table, identifier)
    if not record or (
        record["_owner_id"] != user
        and not (table in {"repositories", "sources", "skills"} and record["_owner_id"] == "demo")
    ):
        raise HTTPException(404, f"{table.rstrip('s').capitalize()} not found.")
    return record


def read_session(cookie: str | None) -> str | None:
    try:
        data = serializer.loads(cookie or "", max_age=60 * 60 * 24 * 30)
        return data.get("user_id") if isinstance(data, dict) else None
    except (BadSignature, SignatureExpired):
        return None


def token_for(user_id: str) -> str:
    account = store.get("accounts", user_id)
    if account and settings.token_encryption_key:
        try:
            return (
                Fernet(settings.token_encryption_key.encode())
                .decrypt(account["encrypted_token"].encode())
                .decode()
            )
        except Exception:
            raise HTTPException(401, "GitHub connection expired. Please sign in again.") from None
    return ""
