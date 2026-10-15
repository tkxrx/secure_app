from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    login = Column(String(32), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    # Время хранится в UTC.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False, default="")
    # Создатель ресурса; ему доступны все действия и выдача прав.
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Явная запись прав (ACL): у кого какие права на чужой ресурс.
# Нет записи = нет прав. Владелец здесь не хранится, его права вычисляются по owner_id.
class ResourcePermission(Base):
    __tablename__ = "resource_permissions"
    # Не больше одной записи прав на пару пользователь-ресурс; повторная выдача её перезаписывает.
    __table_args__ = (UniqueConstraint("user_id", "resource_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Записи прав удаляются вместе с ресурсом.
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    can_read = Column(Boolean, default=False, nullable=False)
    can_update = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
