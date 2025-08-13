# app/models/task_confirmation.py
import uuid
import datetime as dt
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

CONFIRM_STATUS = ("accepted", "rejected", "unclear")

class TaskConfirmation(Base):
    __tablename__ = "task_confirmations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    responder_email: Mapped[str | None] = mapped_column(String(320))
    confirmation_status: Mapped[str] = mapped_column(Enum(*CONFIRM_STATUS, name="confirm_status", native_enum=False))
    raw_response: Mapped[str | None] = mapped_column(Text)
    parsed_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("Task", back_populates="confirmations")