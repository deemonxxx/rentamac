"""SQLAlchemy model for tracking client-node assignment history."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Assignment(Base):
    """Records the history of client-to-node bindings."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="assignments", lazy="selectin")  # noqa: F821
    node: Mapped["Node"] = relationship("Node", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Assignment id={self.id} client_id={self.client_id} "
            f"node_id={self.node_id} assigned_at={self.assigned_at}>"
        )
