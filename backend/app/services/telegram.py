"""Telegram notification service."""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def notify_admin(message: str, parse_mode: str = "HTML") -> bool:
    """Send a notification message to the admin via Telegram Bot API.

    Args:
        message: Message text to send.
        parse_mode: Telegram parse mode ('HTML' or 'MarkdownV2').

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_ADMIN_CHAT_ID:
        logger.warning("Telegram not configured (missing bot token or chat id)")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Telegram notification sent to chat %s", settings.TELEGRAM_ADMIN_CHAT_ID)
            return True
    except httpx.HTTPStatusError as exc:
        logger.error("Telegram API error: %s - %s", exc.response.status_code, exc.response.text)
        return False
    except Exception as exc:
        logger.error("Failed to send Telegram notification: %s", exc)
        return False
