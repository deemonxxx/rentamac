"""SQLAlchemy models for the Client entity."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientStatus(str, enum.Enum):
    """Possible states for a client."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PROVISIONING = "provisioning"
    DEPROVISIONING = "deprovisioning"


class PlanType(str, enum.Enum):
    """Available rental plans — must match landing page tariff selectors."""
    MONTHLY = "monthly"
    ANNUAL = "annual"
    DAILY = "daily"
    HOURLY = "hourly"


class Client(Base):
    """Represents a renter who has access to a macOS node."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, native_enum=False, length=20),
        nullable=False,
    )
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, native_enum=False, length=20),
        default=ClientStatus.INACTIVE,
        nullable=False,
    )
    node_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ssh_user: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    wg_private_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    wg_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    paid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    node: Mapped[Optional["Node"]] = relationship("Node", back_populates="clients", lazy="selectin")  # noqa: F821
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="client", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name!r} status={self.status.value}>"
