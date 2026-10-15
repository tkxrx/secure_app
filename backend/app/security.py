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
