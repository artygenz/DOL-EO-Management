# app/models/task_log.py
import uuid
import datetime as dt
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

TASK_ACTION = ("created", "updated", "completed")

class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(Enum(*TASK_ACTION, name="task_action", native_enum=False))
    notes: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    task = relationship("Task", back_populates="logs")
    actor = relationship("User", back_populates="task_logs")