# app/models/user.py
import uuid
import datetime as dt
from sqlalchemy import String, Boolean, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

USER_ROLE = ("admin", "reviewer", "executor")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(Enum(*USER_ROLE, name="user_role", native_enum=False), default="executor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    org_role: Mapped[str | None] = mapped_column(String(120), index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    assigned_tasks = relationship("Task", back_populates="assignee")
    task_logs = relationship("TaskLog", back_populates="actor")
    tokens = relationship("AuthToken", back_populates="user", cascade="all,delete-orphan")