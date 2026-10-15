import re

from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def check_login(cls, v):
        if len(v) < 3 or len(v) > 32:
            raise ValueError("логин должен быть от 3 до 32 симовлов")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", v):
            raise ValueError("логин может содержать только латинские буквы, цифры, точку, _ и -")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        if len(v) < 8:
            raise ValueError("пароль должен быть не короче 8 символов")
        if not re.search(r"[A-Z]", v):
            raise ValueError("в пароле должна быть заглавная буква")
        if not re.search(r"[a-z]", v):
            raise ValueError("в пароле должна быть строчная буква")
        if not re.search(r"[0-9]", v):
            raise ValueError("в пароле должна быть цифра")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("в пароле должен быть спецсимвол")
        return v
