"""API router for client management — CRUD, assign, and deprovision."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.assignment import Assignment
from app.models.client import Client, ClientStatus
from app.models.node import Node, NodeStatus
from app.schemas.client import AssignRequest, AssignResponse, ClientCreate, ClientOut
from app.services.provision import MacNodeSSH
from app.services.wireguard import WireGuardManager

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("/", response_model=List[ClientOut])
async def list_clients(db: AsyncSession = Depends(get_db)) -> List[Client]:
    """Return all clients."""
    result = await db.execute(select(Client).order_by(Client.id))
    return list(result.scalars().all())


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)) -> Client:
    """Return a single client by ID."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(payload: ClientCreate, db: AsyncSession = Depends(get_db)) -> Client:
    """Create a new client (not yet assigned to a node)."""
    client = Client(**payload.model_dump())
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a client."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await db.delete(client)


@router.post("/assign", response_model=AssignResponse)
async def assign_client(
    payload: AssignRequest,
    db: AsyncSession = Depends(get_db),
) -> AssignResponse:
    """Assign a client to a node: create SSH user, WireGuard config, and record assignment."""
    client = await db.get(Client, payload.client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    node = await db.get(Node, payload.node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if node.status not in (NodeStatus.ONLINE, NodeStatus.OFFLINE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node is in '{node.status.value}' state and cannot accept clients",
        )

    # Determine next WG IP for this client
    wg_mgr = WireGuardManager()
    existing_ips_result = await db.execute(
        select(Client.wg_ip).where(Client.wg_ip.isnot(None))
    )
    existing_ips = [row[0] for row in existing_ips_result.all()]
    client_wg_ip = wg_mgr.next_client_ip(existing_ips)

    # Generate WireGuard keys
    private_key, public_key = wg_mgr.generate_keypair()

    # Create SSH user on the macOS node
    ssh_user = f"client_{client.id}"
    client.status = ClientStatus.PROVISIONING
    await db.flush()

    ssh = MacNodeSSH(host=node.lan_ip)
    try:
        ssh.create_user(ssh_user)
    except Exception as exc:
        client.status = ClientStatus.INACTIVE
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to provision SSH user: {exc}",
        )
    finally:
        ssh.close()

    # Update client record
    client.node_id = node.id
    client.ssh_user = ssh_user
    client.wg_private_key = private_key
    client.wg_ip = client_wg_ip
    client.status = ClientStatus.ACTIVE
    client.paid_until = datetime.now(timezone.utc)

    # Record assignment history
    assignment = Assignment(client_id=client.id, node_id=node.id)
    db.add(assignment)

    await db.flush()
    await db.refresh(assignment)

    return AssignResponse(
        assignment_id=assignment.id,
        client_id=client.id,
        node_id=node.id,
        ssh_user=ssh_user,
        wg_ip=client_wg_ip,
        assigned_at=assignment.assigned_at,
    )


@router.post("/{client_id}/deprovision", response_model=ClientOut)
async def deprovision_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
) -> Client:
    """Remove a client from their assigned node: delete SSH user, release assignment."""
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if not client.node_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client is not assigned to any node",
        )

    node = await db.get(Node, client.node_id)
    if node and client.ssh_user:
        ssh = MacNodeSSH(host=node.lan_ip)
        try:
            ssh.delete_user(client.ssh_user)
        except Exception:
            pass  # Best-effort cleanup
        finally:
            ssh.close()

    # Close open assignment
    result = await db.execute(
        select(Assignment).where(
            Assignment.client_id == client.id,
            Assignment.released_at.is_(None),
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        assignment.released_at = datetime.now(timezone.utc)

    client.node_id = None
    client.ssh_user = None
    client.wg_private_key = None
    client.wg_ip = None
    client.status = ClientStatus.INACTIVE

    await db.flush()
    await db.refresh(client)
    return client
