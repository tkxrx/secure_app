FROM python:3.12-slim

WORKDIR /app

# Сначала только зависимости: слой с pip install кешируется, пока не меняется requirements.txt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Shell-форма CMD нужна для подстановки ${PORT}. Миграции применяются при каждом старте контейнера.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
