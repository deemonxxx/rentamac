"""API router for payment webhooks — YooKassa and crypto."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.client import Client, ClientStatus, PlanType
from app.services.payment import verify_yukassa_signature, verify_crypto_payment
from app.services.telegram import notify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhooks"])

# Plan duration mapping
PLAN_DURATION: dict[PlanType, timedelta] = {
    PlanType.MONTHLY: timedelta(days=30),
    PlanType.ANNUAL: timedelta(days=365),
    PlanType.DAILY: timedelta(days=1),
    PlanType.HOURLY: timedelta(hours=1),
}


def _extend_subscription(client: Client, plan: PlanType | None = None) -> None:
    """Extend the client's paid_until date based on their plan."""
    effective_plan = plan or client.plan
    duration = PLAN_DURATION.get(effective_plan, timedelta(days=30))
    now = datetime.now(timezone.utc)
    base = client.paid_until if client.paid_until and client.paid_until > now else now
    client.paid_until = base + duration


@router.post("/yukassa")
async def webhook_yukassa(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Handle YooKassa payment notification.

    YooKassa sends a JSON body with event type and object containing metadata.
    We verify the signature, find the client by payment_id in metadata, and extend their subscription.
    """
    body = await request.body()

    # Verify signature
    if not verify_yukassa_signature(body, request.headers):
        logger.warning("YooKassa webhook: invalid signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event = payload.get("event", "")
    if event != "payment.succeeded":
        logger.info("YooKassa webhook: ignoring event '%s'", event)
        return {"status": "ignored", "event": event}

    obj = payload.get("object", {})
    metadata = obj.get("metadata", {})
    client_id = metadata.get("client_id")
    plan_str = metadata.get("plan")
    payment_id = obj.get("id", "")

    if not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing client_id in metadata")

    client = await db.get(Client, int(client_id))
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Determine plan
    try:
        plan = PlanType(plan_str) if plan_str else client.plan
    except ValueError:
        plan = client.plan

    client.payment_id = payment_id
    client.status = ClientStatus.ACTIVE
    _extend_subscription(client, plan)

    await db.flush()

    await notify_admin(
        f"💰 YooKassa payment received!\n"
        f"Client: {client.name} (ID: {client.id})\n"
        f"Plan: {plan.value}\n"
        f"Paid until: {client.paid_until}"
    )

    return {"status": "ok", "client_id": client.id, "paid_until": str(client.paid_until)}


@router.post("/crypto")
async def webhook_crypto(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Handle crypto payment notification (NOWPayments / manual confirmation).

    Expected JSON body:
    {
        "payment_id": "...",
        "client_id": 123,
        "plan": "month",
        "status": "finished"
    }
    """
    body = await request.body()

    # Verify crypto payment signature if configured
    if not verify_crypto_payment(body, request.headers):
        logger.warning("Crypto webhook: invalid signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    payment_status = payload.get("status", "")
    if payment_status != "finished":
        logger.info("Crypto webhook: ignoring status '%s'", payment_status)
        return {"status": "ignored", "payment_status": payment_status}

    client_id = payload.get("client_id")
    plan_str = payload.get("plan")
    payment_id = payload.get("payment_id", "")

    if not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing client_id")

    client = await db.get(Client, int(client_id))
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    try:
        plan = PlanType(plan_str) if plan_str else client.plan
    except ValueError:
        plan = client.plan

    client.payment_id = payment_id
    client.status = ClientStatus.ACTIVE
    _extend_subscription(client, plan)

    await db.flush()

    await notify_admin(
        f"🪙 Crypto payment received!\n"
        f"Client: {client.name} (ID: {client.id})\n"
        f"Plan: {plan.value}\n"
        f"Paid until: {client.paid_until}"
    )

    return {"status": "ok", "client_id": client.id, "paid_until": str(client.paid_until)}
