"""Import all models so Alembic and the ORM can discover them."""

from app.models.node import Node, NodeStatus  # noqa: F401
from app.models.client import Client, ClientStatus, PlanType  # noqa: F401
from app.models.assignment import Assignment  # noqa: F401

__all__ = [
    "Node",
    "NodeStatus",
    "Client",
    "ClientStatus",
    "PlanType",
    "Assignment",
]
