import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class MfaSetup:
    secret: str
    otpauth_uri: str
    recovery_codes: list[str]


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def hotp(secret: str, counter: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def verify_code(secret: str, code: str, now: int | None = None) -> bool:
    if not code.isdigit() or len(code) != 6:
        return False
    counter = int((now if now is not None else time.time()) // 30)
    return any(hmac.compare_digest(hotp(secret, counter + offset), code) for offset in (-1, 0, 1))


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def build_setup(user_id, email: str, issuer: str = "NEXUS") -> MfaSetup:
    secret = generate_secret()
    label = f"{issuer}:{email}"
    uri = (
        f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
    )
    return MfaSetup(secret, uri, generate_recovery_codes())
