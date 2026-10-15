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

logging.basicConfig(
    level=logging.INFO,
    format="time=%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="Secure App")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    fields = ",".join(str(e["loc"][-1]) for e in errors)
    # пароль не пишем, только какие поля не прошли
    logger.info("event=validation_error path=%s fields=%s", request.url.path, fields)
    message = "; ".join(e["msg"].replace("Value error, ", "") for e in errors)
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception):
    logger.error("event=server_error path=%s error=%s", request.url.path, repr(exc))
    return JSONResponse(status_code=500, content={"detail": "внутренняя ошибка сервера"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/register", status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.login == data.login).first():
        logger.info("event=register_conflict login=%s", data.login)
        raise HTTPException(status_code=409, detail="логин уже занят")

    user = User(login=data.login, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("event=register_conflict login=%s", data.login)
        raise HTTPException(status_code=409, detail="логин уже занят")

    logger.info("event=register_ok login=%s user_id=%s", user.login, user.id)
    return {"message": "user создан"}


@app.post("/api/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login).first()
    if not user or not verify_password(data.password, user.password_hash):
        logger.info("event=login_failed login=%s", data.login)
        raise HTTPException(status_code=401, detail="неверный логин или пароль")
    logger.info("event=login_ok user_id=%s", user.id)
    return {"access_token": create_token(user.id), "token_type": "bearer"}


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="нужно войти")
    user_id = decode_token(authorization[7:])
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="нужно войти")
    return user


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "login": user.login}


# ---------- ресурсы и права (дискреционная модель) ----------

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


def check_access(db, user, resource_id, action):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="ресурс не найден")
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
        "rights": get_rights(db, user, resource),
    }


@app.get("/api/resources")
def list_resources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    resource = check_access(db, user, resource_id, "update")
    db.query(ResourcePermission).filter(ResourcePermission.resource_id == resource_id).delete()
    db.delete(resource)
    db.commit()
    logger.info("event=resource_deleted user_id=%s resource_id=%s", user.id, resource_id)
    return {"message": "ресурс удалён"}


@app.post("/api/resources/{resource_id}/permissions")
def grant_permission(
    resource_id: int, data: PermissionGrant, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="ресурс не найден")
    if resource.owner_id != user.id:
        logger.info("event=access_denied user_id=%s resource_id=%s action=grant", user.id, resource_id)
        raise HTTPException(status_code=403, detail="выдавать права может только владелец")

    target = db.query(User).filter(User.login == data.login).first()
    if not target:
        raise HTTPException(status_code=404, detail="пользователь не найден")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="у владельца и так есть все права")

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
