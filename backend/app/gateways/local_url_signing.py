import hashlib
import hmac
import time

from app.core.security import SECRET_KEY


def sign(key: str, expiration_seconds: int = 3600) -> tuple[int, str]:
    """
    Build a (expires, signature) pair for a local storage key, so the
    resulting URL is self-contained and fetchable without a login token -
    mirroring how an S3 presigned URL carries its own signature.
    """
    expires = int(time.time()) + max(1, int(expiration_seconds))
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        f"{key}:{expires}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return expires, signature


def verify(key: str, expires: int | None, signature: str | None) -> bool:
    if not expires or not signature:
        return False
    if expires < int(time.time()):
        return False
    expected = hmac.new(
        SECRET_KEY.encode("utf-8"),
        f"{key}:{expires}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
