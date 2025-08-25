# app/models/executive_order.py
import uuid
import datetime as dt
from sqlalchemy import String, Text, DateTime, Enum, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

EO_STATUS = ("processed", "error", "pending", "received")

class ExecutiveOrder(Base):
    __tablename__ = "executive_orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_email: Mapped[str | None] = mapped_column(String(320), index=True)
    received_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_url: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(Enum(*EO_STATUS, name="eo_status", native_enum=False), default="pending")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


    tasks = relationship("Task", back_populates="executive_order", cascade="all,delete-orphan")
    email_logs = relationship("EmailLog", back_populates="related_eo", cascade="all,delete-orphan")