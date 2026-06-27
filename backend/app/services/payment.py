"""Payment service — YooKassa and crypto payment helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def create_yukassa_payment(
    amount: str,
    currency: str = "RUB",
    description: str = "RentaMac subscription",
    metadata: Optional[Dict[str, str]] = None,
    return_url: str = "https://rentamac.ru/payment/success",
) -> Dict[str, Any]:
    """Create a payment via YooKassa API.

    Args:
        amount: Payment amount as string (e.g., "2990.00").
        currency: Currency code.
        description: Human-readable payment description.
        metadata: Arbitrary key-value metadata attached to the payment.
        return_url: URL to redirect user after payment.

    Returns:
        YooKassa payment object dict with 'id', 'confirmation', 'status', etc.

    Raises:
        httpx.HTTPStatusError: If YooKassa returns an error.
    """
    idempotence_key = str(uuid.uuid4())

    payload = {
        "amount": {"value": amount, "currency": currency},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": description,
        "metadata": metadata or {},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",
            json=payload,
            auth=(settings.YUKASSA_SHOP_ID, settings.YUKASSA_SECRET_KEY),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


def verify_yukassa_signature(body: bytes, headers: dict) -> bool:
    """Verify a YooKassa webhook signature.

    YooKassa signs webhook payloads using HMAC-SHA256 with the secret key.
    The signature is sent in the 'Signature' header.

    Args:
        body: Raw request body bytes.
        headers: Request headers dict.

    Returns:
        True if signature is valid, False otherwise.
    """
    signature = headers.get("signature") or headers.get("Signature")
    if not signature:
        logger.warning("YooKassa webhook: no signature header found")
        # In development, allow unsigned webhooks
        if not settings.YUKASSA_SECRET_KEY:
            return True
        return False

    if not settings.YUKASSA_SECRET_KEY:
        logger.warning("YooKassa secret key not configured, skipping verification")
        return True

    expected = hmac.new(
        settings.YUKASSA_SECRET_KEY.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature.lower(), expected.lower())


async def verify_crypto_payment(body: bytes, headers: dict) -> bool:
    """Verify a crypto payment webhook signature.

    NOWPayments sends an 'x-nowpayments-sig' header with HMAC-SHA512 signature.

    Args:
        body: Raw request body bytes.
        headers: Request headers dict.

    Returns:
        True if signature is valid, False otherwise.
    """
    signature = headers.get("x-nowpayments-sig") or headers.get("X-Nowpayments-Sig")
    if not signature:
        logger.warning("Crypto webhook: no signature header found")
        # In development, allow unsigned webhooks
        if not settings.NOWPAYMENTS_API_KEY:
            return True
        return False

    if not settings.NOWPAYMENTS_API_KEY:
        logger.warning("NOWPayments API key not configured, skipping verification")
        return True

    # Sort JSON keys and compute HMAC-SHA512
    sorted_body = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(
        settings.NOWPAYMENTS_API_KEY.encode(),
        sorted_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(signature.lower(), expected.lower())
