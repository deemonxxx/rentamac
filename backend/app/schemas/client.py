"""Pydantic schemas for the Client entity."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.client import ClientStatus, PlanType


class ClientCreate(BaseModel):
    """Schema for creating a new client."""
    name: str = Field(..., min_length=1, max_length=200, examples=["Ivan Petrov"])
    email: Optional[str] = Field(None, max_length=255, examples=["ivan@example.com"])
    telegram: Optional[str] = Field(None, max_length=100, examples=["@ivan_petrov"])
    plan: PlanType = Field(..., examples=[PlanType.MONTHLY])


class ClientOut(BaseModel):
    """Schema for returning client data in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: Optional[str] = None
    telegram: Optional[str] = None
    plan: PlanType
    status: ClientStatus
    node_id: Optional[int] = None
    ssh_user: Optional[str] = None
    wg_private_key: Optional[str] = None
    wg_ip: Optional[str] = None
    paid_until: Optional[datetime] = None
    payment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AssignRequest(BaseModel):
    """Request to assign a client to a node."""
    client_id: int
    node_id: int


class AssignResponse(BaseModel):
    """Response after assigning a client to a node."""
    assignment_id: int
    client_id: int
    node_id: int
    ssh_user: str
    wg_ip: str
    assigned_at: datetime
