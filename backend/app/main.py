import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate
from app.security import hash_password

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
