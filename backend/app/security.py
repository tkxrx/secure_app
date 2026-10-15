from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError

from app.config import settings

# Падаем при импорте, чтобы приложение не стартовало с неподдерживаемой схемой.
if settings.HASH_SCHEME != "argon2id":
    raise ValueError("поддерживается только HASH_SCHEME=argon2id")

# Один экземпляр на всё приложение; параметры попадают в строку хеша,
# поэтому verify работает и с хешами, созданными при других настройках.
ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    # Type.ID = argon2id. Соль генерируется на каждый хеш и хранится внутри строки хеша.
    type=Type.ID,
)


def hash_password(password):
    return ph.hash(password)


def verify_password(password, password_hash):
    # VerificationError покрывает неверный пароль.
    try:
        return ph.verify(password_hash, password)
    except VerificationError:
        return False


def create_token(user_id):
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    # sub строкой: PyJWT требует, чтобы claim sub был str.
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token):
    # Алгоритм зафиксирован списком, так что токен с alg=none или другим алгоритмом не пройдёт.
    # exp проверяется автоматически; любая ошибка (просрочен, подделан, мусор) = None.
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return int(data["sub"])
    except Exception:
        return None
