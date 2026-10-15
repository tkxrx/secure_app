# Secure App

Лабораторная работа по безопасному программированию. Вариант 2 — дискреционная модель доступа.

Регистрация пользователя через форму, пароль хранится как хэш Argon2id. После входа пользователь может создавать ресурсы
и выдавать другим пользователям права на чтение, изменение и удаление своих ресурсов.

Стек: React + TypeScript (Vite), FastAPI, SQLAlchemy, Alembic, PostgreSQL, Docker.

## Запуск

```
docker compose up --build
```

- фронтенд: http://localhost:8080
- бэкенд: http://localhost:8000 (документация API http://localhost:8000/docs)

Миграции применяются автоматически при старте бэкенда.

Тесты:

```
docker compose exec backend pytest
```

### Без докера

```
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # поправить DATABASE_URL под свою базу
alembic upgrade head
uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

## Структура

```
backend/
  app/
    main.py        - все эндпоинты, проверка прав, логирование
    models.py      - таблицы users, resources, resource_permissions
    schemas.py     - валидация входных данных
    security.py    - хэширование паролей (argon2id) и JWT
    config.py      - настройки из переменных окружения
    database.py    - подключение к БД
  alembic/         - миграции
  tests/           - тесты pytest
frontend/
  src/pages/       - Register, Login, Resources
  src/api.ts       - запросы к бэкенду
  nginx.conf       - раздача фронта и проксирование /api на бэкенд
docs/              - скриншоты
docker-compose.yml
.env.example
```

## API

| Метод | URL | Описание |
|---|---|---|
| POST | /api/register | регистрация |
| POST | /api/login | вход, возвращает токен |
| GET | /api/me | текущий пользователь |
| GET | /api/resources | список ресурсов и мои права на них |
| POST | /api/resources | создать ресурс |
| GET | /api/resources/{id} | прочитать (нужно право read) |
| PUT | /api/resources/{id} | изменить (нужно право update) |
| DELETE | /api/resources/{id} | удалить (нужно право delete) |
| POST | /api/resources/{id}/permissions | выдать права (только владелец) |

Все запросы к ресурсам требуют заголовок `Authorization: Bearer <token>`.

Ответы с ошибками: 422 — ошибка валидации, 409 — логин занят, 401 — не авторизован, 403 — нет прав, 404 — не найдено.

### Примеры curl

Регистрация:

```
curl -X POST http://localhost:8000/api/register -H "Content-Type: application/json" \
  -d '{"login": "alice", "password": "Qwerty!123"}'

{"message":"user создан"}
```

Слабый пароль:

```
curl -X POST http://localhost:8000/api/register -H "Content-Type: application/json" \
  -d '{"login": "bob", "password": "qwerty"}'

{"detail":"пароль должен быть не короче 8 символов"}
```

Вход:

```
curl -X POST http://localhost:8000/api/login -H "Content-Type: application/json" \
  -d '{"login": "alice", "password": "Qwerty!123"}'

{"access_token":"eyJ...","token_type":"bearer"}
```

Создать ресурс и выдать bob право на чтение:

```
curl -X POST http://localhost:8000/api/resources -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"title": "Отчёт", "content": "секрет"}'

curl -X POST http://localhost:8000/api/resources/1/permissions -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"login": "bob", "can_read": true}'
```

Пользователь без прав:

```
curl http://localhost:8000/api/resources/1 -H "Authorization: Bearer $EVE_TOKEN"

{"detail":"нет права на read"}
```

## Модель доступа

У каждого ресурса есть владелец — пользователь, который его создал. Владелец имеет все права на свой ресурс.
Остальным пользователям права выдаёт владелец через таблицу `resource_permissions`
(`user_id`, `resource_id`, `can_read`, `can_update`, `can_delete`). Если записи нет — доступа нет.

Проверка делается на бэкенде (функция `check_access` в `main.py`) перед чтением, изменением и удалением.
На фронте кнопки показываются всем, но при отсутствии права бэкенд возвращает 403 и фронт показывает ошибку.

## Безопасность: что сделано

- пароли хэшируются Argon2id (argon2-cffi), соль генерируется автоматически для каждого пароля
- параметры хэширования вынесены в конфиг: `ARGON2_TIME_COST`, `ARGON2_MEMORY_COST`, `ARGON2_PARALLELISM`
- пароль не хранится в открытом виде и не пишется в логи (в логах только логин и событие)
- уникальный индекс на `users.login`, повторная регистрация возвращает 409
- валидация логина и пароля на бэкенде, ошибки 422 с понятным текстом
- права доступа проверяются на бэкенде, а не только на фронте
- запросы к БД через SQLAlchemy ORM (без склейки SQL строк)
- секреты не хранятся в репозитории, есть только `.env.example`

## Логи

Пример логов бэкенда (`docker compose logs backend`):

```
time=2026-10-15 19:20:11,402 level=INFO logger=app event=register_ok login=alice user_id=1
time=2026-10-15 19:20:15,118 level=INFO logger=app event=register_conflict login=alice
time=2026-10-15 19:20:21,733 level=INFO logger=app event=validation_error path=/api/register fields=password
time=2026-10-15 19:22:40,051 level=INFO logger=app event=permission_granted owner_id=1 target=bob resource_id=1 read=True update=False delete=False
time=2026-10-15 19:23:02,694 level=INFO logger=app event=access_denied user_id=3 resource_id=1 action=read
```

## Тесты

- `test_register.py` — успешная регистрация, повторный логин, слабый пароль
- `test_access.py` — доступ после выдачи права, отказ без права, право на чтение не даёт удалять, выдавать права может только владелец

## Участники

- Коротких Тимофей — бэкенд (регистрация, авторизация, проверка прав), докер, тесты
- Рощупкин Максим — фронтенд, база данных (модели, миграции), README
