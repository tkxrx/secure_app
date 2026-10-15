import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginData, UserCreate
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
