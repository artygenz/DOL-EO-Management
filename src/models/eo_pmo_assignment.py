import uuid
import datetime as dt
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class EOPMOAssignment(Base):
    __tablename__ = "eo_pmo_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executive_orders.id", ondelete="CASCADE"), nullable=False)
    pmo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    executive_order = relationship("ExecutiveOrder", back_populates="pmo_assignments")
    pmo = relationship("User", foreign_keys=[pmo_id], back_populates="eo_pmo_assignments")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    
    # Ensure unique EO-PMO combinations
    __table_args__ = (
        UniqueConstraint('eo_id', 'pmo_id', name='uq_eo_pmo_assignment'),
    )
