import uuid
import datetime as dt
from sqlalchemy import String, Text, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class DailyEOSummary(Base):
    __tablename__ = "daily_eo_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executive_orders.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(index=True)
    progress_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_blockers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    risks: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    attention_items: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    missing_updates: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # List of user emails who didn't report
    total_tasks: Mapped[int] = mapped_column(default=0)
    updated_tasks: Mapped[int] = mapped_column(default=0)
    summary_email_sent: Mapped[bool] = mapped_column(default=False)
    summary_email_sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    executive_order = relationship("ExecutiveOrder", back_populates="daily_summaries")
