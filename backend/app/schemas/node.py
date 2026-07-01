"""Pydantic schemas for the Node entity."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.node import NodeStatus


class NodeCreate(BaseModel):
    """Schema for creating a new node."""
    name: str = Field(..., min_length=1, max_length=100, examples=["mac-mini-01"])
    lan_ip: str = Field(..., min_length=7, max_length=45, examples=["192.168.1.100"])
    wg_ip: Optional[str] = Field(None, max_length=45, examples=["10.0.0.1"])
    wg_public_key: Optional[str] = Field(None, max_length=64)
    status: NodeStatus = NodeStatus.OFFLINE
    hardware: Optional[str] = Field(None, examples=["Mac Mini M4, 16GB RAM, 512GB SSD"])
    macos_version: Optional[str] = Field(None, max_length=50, examples=["15.0"])
    rustdesk_id: Optional[str] = Field(None, max_length=20, examples=["172925881"])
    ssh_port: int = Field(22, examples=[22])


class NodeUpdate(BaseModel):
    """Schema for updating an existing node (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    lan_ip: Optional[str] = Field(None, min_length=7, max_length=45)
    wg_ip: Optional[str] = Field(None, max_length=45)
    wg_public_key: Optional[str] = Field(None, max_length=64)
    status: Optional[NodeStatus] = None
    hardware: Optional[str] = None
    macos_version: Optional[str] = Field(None, max_length=50)
    rustdesk_id: Optional[str] = Field(None, max_length=20)
    ssh_port: Optional[int] = None


class NodeOut(BaseModel):
    """Schema for returning node data in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lan_ip: str
    wg_ip: Optional[str] = None
    wg_public_key: Optional[str] = None
    status: NodeStatus
    hardware: Optional[str] = None
    macos_version: Optional[str] = None
    rustdesk_id: Optional[str] = None
    ssh_port: int = 22
    created_at: datetime
    updated_at: datetime


class NodeStats(BaseModel):
    """Aggregated node statistics."""
    total: int
    online: int
    offline: int
    maintenance: int
    provisioning: int
