from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL)
# autoflush=False: изменения отправляются в БД только при явном commit/flush.
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Базовый класс моделей; его metadata используют alembic и тесты.
Base = declarative_base()


# Зависимость FastAPI: одна сессия на запрос, закрывается после ответа даже при исключении.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
