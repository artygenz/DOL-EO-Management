# app/models/task.py
import uuid
import datetime as dt
from sqlalchemy import String, Text, Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

TASK_STATUS = ("pending", "in_progress", "completed", "Pending PMO approval", "approved", "rejected")
TASK_PRIORITY = ("low", "medium", "high")

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executive_orders.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(Enum(*TASK_STATUS, name="task_status", native_enum=False), default="pending")
    due_date: Mapped[dt.date | None]
    category: Mapped[str | None] = mapped_column(String(255), index=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


    executive_order = relationship("ExecutiveOrder", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all,delete-orphan")
    confirmations = relationship("TaskConfirmation", back_populates="task", cascade="all,delete-orphan")
    daily_updates = relationship("DailyUpdate", back_populates="task")