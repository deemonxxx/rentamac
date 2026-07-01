"""SQLAlchemy models for the Node entity."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NodeStatus(str, enum.Enum):
    """Possible states for a macOS node."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    PROVISIONING = "provisioning"


class Node(Base):
    """Represents a physical macOS machine in the cluster."""

    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    lan_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    wg_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    wg_public_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[NodeStatus] = mapped_column(
        Enum(NodeStatus, native_enum=False, length=20),
        default=NodeStatus.OFFLINE,
        nullable=False,
    )
    hardware: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    macos_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rustdesk_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    rustdesk_password: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ssh_port: Mapped[int] = mapped_column(default=22, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    clients: Mapped[list["Client"]] = relationship("Client", back_populates="node", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Node id={self.id} name={self.name!r} status={self.status.value}>"
