from pydantic_settings import BaseSettings


# Значения ниже - дефолты для локального запуска; переменные окружения и .env их перекрывают.
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/secure_app"
    SECRET_KEY: str = "dev-secret"
    APP_ENV: str = "dev"
    PORT: int = 8000

    # Параметры argon2id. MEMORY_COST в КиБ: 65536 = 64 МиБ на один хеш.
    HASH_SCHEME: str = "argon2id"
    # TIME_COST - число проходов по памяти, PARALLELISM - число потоков.
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 2

    # Время жизни JWT в минутах.
    TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
