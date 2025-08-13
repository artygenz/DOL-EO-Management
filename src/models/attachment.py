# app/models/attachment.py
import uuid
import datetime as dt
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("email_logs.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_url: Mapped[str] = mapped_column(String(2048))
    file_type: Mapped[str | None] = mapped_column(String(120))
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    email_log = relationship("EmailLog", back_populates="attachments")