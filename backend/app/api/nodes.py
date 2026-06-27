"""API router for node management — CRUD, stats, and reboot."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.node import Node, NodeStatus
from app.schemas.node import NodeCreate, NodeOut, NodeStats, NodeUpdate
from app.services.provision import MacNodeSSH

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("/", response_model=List[NodeOut])
async def list_nodes(db: AsyncSession = Depends(get_db)) -> List[Node]:
    """Return all nodes."""
    result = await db.execute(select(Node).order_by(Node.id))
    return list(result.scalars().all())


@router.get("/stats", response_model=NodeStats)
async def node_stats(db: AsyncSession = Depends(get_db)) -> NodeStats:
    """Return aggregated node statistics."""
    result = await db.execute(
        select(Node.status, func.count(Node.id)).group_by(Node.status)
    )
    counts: dict[str, int] = {row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in result.all()}
    return NodeStats(
        total=sum(counts.values()),
        online=counts.get("online", 0),
        offline=counts.get("offline", 0),
        maintenance=counts.get("maintenance", 0),
        provisioning=counts.get("provisioning", 0),
    )


@router.get("/{node_id}", response_model=NodeOut)
async def get_node(node_id: int, db: AsyncSession = Depends(get_db)) -> Node:
    """Return a single node by ID."""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.post("/", response_model=NodeOut, status_code=status.HTTP_201_CREATED)
async def create_node(payload: NodeCreate, db: AsyncSession = Depends(get_db)) -> Node:
    """Create a new node."""
    node = Node(**payload.model_dump())
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return node


@router.patch("/{node_id}", response_model=NodeOut)
async def update_node(
    node_id: int,
    payload: NodeUpdate,
    db: AsyncSession = Depends(get_db),
) -> Node:
    """Partially update a node."""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)

    await db.flush()
    await db.refresh(node)
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a node."""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    await db.delete(node)


@router.post("/{node_id}/reboot", response_model=NodeOut)
async def reboot_node(node_id: int, db: AsyncSession = Depends(get_db)) -> Node:
    """Reboot a macOS node via SSH."""
    node = await db.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    ssh = MacNodeSSH(host=node.lan_ip)
    try:
        ssh.reboot()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reboot node: {exc}",
        )
    finally:
        ssh.close()

    node.status = NodeStatus.PROVISIONING
    await db.flush()
    await db.refresh(node)
    return node
