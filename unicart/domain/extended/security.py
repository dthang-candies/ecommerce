"""Password hashing (NFR-03): salted PBKDF2-HMAC-SHA256, standard library only."""
import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 240_000


def hash_password(raw: str, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("ascii"), iterations)
    return f"{_ALGO}${iterations}${salt}${digest.hex()}"


def is_hashed(value: str) -> bool:
    return value.startswith(_ALGO + "$")


def verify_password(raw: str, stored: str) -> bool:
    try:
        algo, iterations, salt, expected = stored.split("$")
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("ascii"), int(iterations))
    except (ValueError, UnicodeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)
