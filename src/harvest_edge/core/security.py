import hashlib
import hmac
import secrets


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw_key = f"he_live_{secrets.token_urlsafe(32)}"
    return raw_key, hash_api_key(raw_key), raw_key[:8]


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), stored_hash)
