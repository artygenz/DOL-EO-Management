import uuid
import datetime as dt
from sqlalchemy import String, Text, Integer, Numeric, DateTime, func, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

TASK_UPDATE_STATUS = ("NotStarted", "InProgress", "Blocked", "Completed")

class TaskUpdate(Base):
    __tablename__ = "task_updates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executive_orders.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(index=True)
    progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(Enum(*TASK_UPDATE_STATUS, name="task_update_status", native_enum=False), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    risks: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    eta: Mapped[dt.date | None] = mapped_column(nullable=True)
    spent_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI-generated summary for this task update
    source_email_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_late: Mapped[bool] = mapped_column(default=False)
    
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    executive_order = relationship("ExecutiveOrder", back_populates="task_updates")
    task = relationship("Task", back_populates="task_updates")
    user = relationship("User", back_populates="task_updates")
