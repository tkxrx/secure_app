from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError

from app.config import settings

if settings.HASH_SCHEME != "argon2id":
    raise ValueError("поддерживается только HASH_SCHEME=argon2id")

ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    type=Type.ID,
)


def hash_password(password):
    return ph.hash(password)


def verify_password(password, password_hash):
    try:
        return ph.verify(password_hash, password)
    except VerificationError:
        return False


def create_token(user_id):
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return int(data["sub"])
    except Exception:
        return None
