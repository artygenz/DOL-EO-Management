import uuid
import datetime as dt
from sqlalchemy import String, Text, Integer, Numeric, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class DailyUpdate(Base):
    __tablename__ = "daily_updates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    update_text: Mapped[str] = mapped_column(Text, nullable=False)
    progress_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hours_spent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    status_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    next_actions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="daily_updates")
    user = relationship("User", back_populates="daily_updates")
