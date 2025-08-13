# app/models/email_log.py
import uuid
import datetime as dt
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

DIRECTION = ("incoming", "outgoing")

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    direction: Mapped[str] = mapped_column(Enum(*DIRECTION, name="email_direction", native_enum=False))
    subject: Mapped[str | None] = mapped_column(String(500))
    sender: Mapped[str | None] = mapped_column(String(320))
    recipients: Mapped[list[str] | None] = mapped_column(ARRAY(TEXT))
    raw_content: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_eo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("executive_orders.id", ondelete="SET NULL"), index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    related_eo = relationship("ExecutiveOrder", back_populates="email_logs")
    attachments = relationship("Attachment", back_populates="email_log", cascade="all,delete-orphan")