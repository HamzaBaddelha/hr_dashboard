import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(32).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt, hashed = stored_hash.split("$", 1)
        return hashlib.sha256((salt + plain_password).encode()).hexdigest() == hashed
    except Exception:
        return False
