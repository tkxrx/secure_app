from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    login: str
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        if len(v) < 8:
            raise ValueError("пароль должен быть не короче 8 символов")
        return v
