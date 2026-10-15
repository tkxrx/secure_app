import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Resource, ResourcePermission, User
from app.schemas import LoginData, PermissionGrant, ResourceCreate, ResourceUpdate, UserCreate
from app.security import create_token, decode_token, hash_password, verify_password

# Логи в формате key=value, чтобы их было удобно грепать и парсить.
logging.basicConfig(
    level=logging.INFO,
    format="time=%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="Secure App")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Ошибки pydantic превращаются в одну строку на русском вместо стандартного списка FastAPI.
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # loc[-1] = имя поля (например password).
    # Имена полей, не прошедших проверку, для лога.
    fields = ",".join(str(e["loc"][-1]) for e in errors)
    # пароль не пишем, только какие поля не прошли
    logger.info("event=validation_error path=%s fields=%s", request.url.path, fields)
    # pydantic добавляет префикс 'Value error, ' к ValueError из валидаторов, убираем его.
    message = "; ".join(e["msg"].replace("Value error, ", "") for e in errors)
    return JSONResponse(status_code=422, content={"detail": message})


# Последний рубеж: наружу только общий текст, детали (repr) только в лог.
# HTTPException сюда не попадают, их обрабатывает сам FastAPI.
@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception):
    logger.error("event=server_error path=%s error=%s", request.url.path, repr(exc))
    return JSONResponse(status_code=500, content={"detail": "внутренняя ошибка сервера"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/register", status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    # Быстрая проверка ради понятного 409. Гонку двух одновременных регистраций
    # ловит уникальный индекс в БД (IntegrityError ниже).
    if db.query(User).filter(User.login == data.login).first():
        logger.info("event=register_conflict login=%s", data.login)
        raise HTTPException(status_code=409, detail="логин уже занят")

    user = User(login=data.login, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Откат возвращает сессию в рабочее состояние после неудачного commit.
        db.rollback()
        logger.info("event=register_conflict login=%s", data.login)
        raise HTTPException(status_code=409, detail="логин уже занят")

    # user.id заполняется БД при commit.
    logger.info("event=register_ok login=%s user_id=%s", user.login, user.id)
    return {"message": "user создан"}


@app.post("/api/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login).first()
    # Одна ошибка на оба случая, чтобы по ответу нельзя было узнать, существует ли логин.
    if not user or not verify_password(data.password, user.password_hash):
        logger.info("event=login_failed login=%s", data.login)
        raise HTTPException(status_code=401, detail="неверный логин или пароль")
    logger.info("event=login_ok user_id=%s", user.id)
    return {"access_token": create_token(user.id), "token_type": "bearer"}


# Зависимость для защищённых эндпоинтов: заголовок 'Authorization: Bearer <jwt>' -> User или 401.
# Без заголовка Authorization приходит пустая строка, и запрос получает 401.
def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="нужно войти")
    # [7:] отрезает 'Bearer '.
    user_id = decode_token(authorization[7:])
    # Пользователя достаём из БД: токен удалённого пользователя перестаёт работать.
    # Для невалидного токена запрос в БД не выполняется.
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="нужно войти")
    return user


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "login": user.login}


# ---------- ресурсы и права (дискреционная модель) ----------

# Возвращает словарь прав user на resource. Владелец может всё,
# остальные - только то, что записано в ResourcePermission (по умолчанию запрет).
def get_rights(db, user, resource):
    if resource.owner_id == user.id:
        return {"read": True, "update": True, "delete": True}
    perm = (
        db.query(ResourcePermission)
        .filter(ResourcePermission.user_id == user.id, ResourcePermission.resource_id == resource.id)
        .first()
    )
    if not perm:
        return {"read": False, "update": False, "delete": False}
    return {"read": perm.can_read, "update": perm.can_update, "delete": perm.can_delete}


# Общая проверка для read/update/delete: 404, если ресурса нет, 403, если нет права action.
def check_access(db, user, resource_id, action):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="ресурс не найден")
    # action совпадает с ключом словаря из get_rights: read, update или delete.
    if not get_rights(db, user, resource)[action]:
        logger.info("event=access_denied user_id=%s resource_id=%s action=%s", user.id, resource_id, action)
        raise HTTPException(status_code=403, detail=f"нет права на {action}")
    return resource


def resource_to_dict(db, resource, user):
    owner = db.get(User, resource.owner_id)
    return {
        "id": resource.id,
        "title": resource.title,
        "owner": owner.login,
        # Права текущего пользователя на этот ресурс.
        "rights": get_rights(db, user, resource),
    }


# Список виден всем вошедшим: название и владелец открыты, содержимое отдаёт только read_resource.
@app.get("/api/resources")
def list_resources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Сортировка по id даёт стабильный порядок строк в таблице на фронте.
    resources = db.query(Resource).order_by(Resource.id).all()
    return [resource_to_dict(db, r, user) for r in resources]


@app.post("/api/resources", status_code=201)
def create_resource(data: ResourceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = Resource(title=data.title, content=data.content, owner_id=user.id)
    db.add(resource)
    db.commit()
    logger.info("event=resource_created user_id=%s resource_id=%s", user.id, resource.id)
    return resource_to_dict(db, resource, user)


@app.get("/api/resources/{resource_id}")
def read_resource(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = check_access(db, user, resource_id, "read")
    result = resource_to_dict(db, resource, user)
    # content добавляется только здесь, после проверки права read.
    result["content"] = resource.content
    return result


@app.put("/api/resources/{resource_id}")
def update_resource(
    resource_id: int, data: ResourceUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    resource = check_access(db, user, resource_id, "update")
    if data.title is not None:
        resource.title = data.title
    if data.content is not None:
        resource.content = data.content
    db.commit()
    logger.info("event=resource_updated user_id=%s resource_id=%s", user.id, resource_id)
    return {"message": "ресурс изменён"}


@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = check_access(db, user, resource_id, "delete")
    # Сначала удаляются права на ресурс, затем сам ресурс.
    db.query(ResourcePermission).filter(ResourcePermission.resource_id == resource_id).delete()
    db.delete(resource)
    db.commit()
    logger.info("event=resource_deleted user_id=%s resource_id=%s", user.id, resource_id)
    return {"message": "ресурс удалён"}


@app.post("/api/resources/{resource_id}/permissions")
def grant_permission(
    resource_id: int, data: PermissionGrant, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # Выдавать права может только владелец; право update/delete на ресурс не даёт права раздавать доступ.
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="ресурс не найден")
    if resource.owner_id != user.id:
        logger.info("event=access_denied user_id=%s resource_id=%s action=grant", user.id, resource_id)
        raise HTTPException(status_code=403, detail="выдавать права может только владелец")

    # target - пользователь, которому выдаются права.
    target = db.query(User).filter(User.login == data.login).first()
    if not target:
        raise HTTPException(status_code=404, detail="пользователь не найден")
    # Владельцу права не выдаются: они вычисляются по owner_id.
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="у владельца и так есть все права")

    # upsert: создаём запись или перезаписываем существующую.
    perm = (
        db.query(ResourcePermission)
        .filter(ResourcePermission.user_id == target.id, ResourcePermission.resource_id == resource_id)
        .first()
    )
    if not perm:
        perm = ResourcePermission(user_id=target.id, resource_id=resource_id)
        db.add(perm)
    perm.can_read = data.can_read
    perm.can_update = data.can_update
    perm.can_delete = data.can_delete
    db.commit()

    logger.info(
        "event=permission_granted owner_id=%s target=%s resource_id=%s read=%s update=%s delete=%s",
        user.id, target.login, resource_id, data.can_read, data.can_update, data.can_delete,
    )
    return {"message": f"права для {target.login} сохранены"}
