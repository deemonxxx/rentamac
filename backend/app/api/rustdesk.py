"""API router for RustDesk remote access management."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.node import Node, NodeStatus
from app.services.provision import MacNodeSSH

router = APIRouter(prefix="/api/nodes", tags=["rustdesk"])


class RustDeskInfo(BaseModel):
    """RustDesk connection info for a node."""
    node_id: int
    node_name: str
    rustdesk_id: Optional[str] = None
    rustdesk_password: Optional[str] = None
    id_server: str
    relay_server: str
    key: str


class RustDeskPasswordRequest(BaseModel):
    """Request to set a RustDesk password."""
    password: Optional[str] = Field(
        None,
        min_length=4,
        max_length=50,
        description="Password to set. If empty, generates a random 8-char password.",
    )


class RustDeskPasswordResponse(BaseModel):
    """Response after setting a RustDesk password."""
    node_id: int
    password: str
    message: str


class CleanupResponse(BaseModel):
    """Response after cleanup."""
    node_id: int
    message: str


def _get_ssh(node: Node) -> MacNodeSSH:
    """Create SSH connection to a node's Mac.

    Uses reverse SSH tunnel (localhost:2222) for Mac access.
    With network_mode: host, container shares host network stack.
    """
    return MacNodeSSH(host="localhost", port=2222, username="qwerty")


@router.get("/{node_id}/rustdesk", response_model=RustDeskInfo)
async def get_rustdesk_info(
    node_id: int,
    db: AsyncSession = Depends(get_db),
) -> RustDeskInfo:
    """Get RustDesk connection info for a node.

    Returns the RustDesk ID, password, and server settings
    needed for a client to connect.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )

    return RustDeskInfo(
        node_id=node.id,
        node_name=node.name,
        rustdesk_id=node.rustdesk_id,
        rustdesk_password=node.rustdesk_password,
        id_server=f"{settings.RUSTDESK_SERVER_IP}:{settings.RUSTDESK_ID_PORT}",
        relay_server=f"{settings.RUSTDESK_SERVER_IP}:{settings.RUSTDESK_RELAY_PORT}",
        key=settings.RUSTDESK_KEY,
    )


@router.post("/{node_id}/rustdesk/password", response_model=RustDeskPasswordResponse)
async def set_rustdesk_password(
    node_id: int,
    payload: RustDeskPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> RustDeskPasswordResponse:
    """Set or generate a RustDesk permanent password on a node.

    If no password is provided, generates a random 8-character password.
    The password is written to the Mac's RustDesk config and stored in DB.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )

    password = payload.password or secrets.token_urlsafe(8)[:12]

    ssh = _get_ssh(node)
    try:
        ssh.set_rustdesk_password(password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to set RustDesk password: {exc}",
        )
    finally:
        ssh.close()

    node.rustdesk_password = password
    await db.flush()
    await db.refresh(node)

    return RustDeskPasswordResponse(
        node_id=node.id,
        password=password,
        message="RustDesk password set successfully",
    )


@router.delete("/{node_id}/rustdesk/password", response_model=RustDeskPasswordResponse)
async def clear_rustdesk_password(
    node_id: int,
    db: AsyncSession = Depends(get_db),
) -> RustDeskPasswordResponse:
    """Clear the RustDesk password on a node.

    Removes the permanent password. After RustDesk restarts, a new
    random temporary password will be generated (visible on screen only).
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )

    ssh = _get_ssh(node)
    try:
        ssh.clear_rustdesk_password()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to clear RustDesk password: {exc}",
        )
    finally:
        ssh.close()

    node.rustdesk_password = None
    await db.flush()
    await db.refresh(node)

    return RustDeskPasswordResponse(
        node_id=node.id,
        password="",
        message="RustDesk password cleared. New temp password will appear on Mac screen.",
    )


@router.post("/{node_id}/rustdesk/sync", response_model=RustDeskInfo)
async def sync_rustdesk_id(
    node_id: int,
    db: AsyncSession = Depends(get_db),
) -> RustDeskInfo:
    """Sync the RustDesk ID from the Mac to the database.

    Reads the current RustDesk ID from the Mac's config and updates DB.
    Use this after initial RustDesk setup on a new Mac.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )

    ssh = _get_ssh(node)
    try:
        rd_id = ssh.get_rustdesk_id()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read RustDesk ID: {exc}",
        )
    finally:
        ssh.close()

    if rd_id:
        node.rustdesk_id = rd_id
        await db.flush()
        await db.refresh(node)

    return RustDeskInfo(
        node_id=node.id,
        node_name=node.name,
        rustdesk_id=node.rustdesk_id,
        rustdesk_password=node.rustdesk_password,
        id_server=f"{settings.RUSTDESK_SERVER_IP}:{settings.RUSTDESK_ID_PORT}",
        relay_server=f"{settings.RUSTDESK_SERVER_IP}:{settings.RUSTDESK_RELAY_PORT}",
        key=settings.RUSTDESK_KEY,
    )


@router.post("/{node_id}/cleanup", response_model=CleanupResponse)
async def cleanup_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
) -> CleanupResponse:
    """Clean up client data on a node between rentals.

    Removes browser data, downloads, desktop files, caches,
    and shell history. Does NOT delete the user account.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )

    ssh = _get_ssh(node)
    try:
        ssh.cleanup_client_data()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to cleanup node: {exc}",
        )
    finally:
        ssh.close()

    return CleanupResponse(
        node_id=node.id,
        message="Client data cleaned up successfully",
    )
