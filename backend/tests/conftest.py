import os

# Переменные окружения ставятся до импорта app: settings читаются один раз при импорте app.config.
# Тесты работают на SQLite, параметры argon2 уменьшены для скорости.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "8192"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


# Каждый тест получает чистую схему БД.
@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # TestClient в блоке with запускает события startup/shutdown; после теста схема удаляется.
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(engine)
