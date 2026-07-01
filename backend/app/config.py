"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rentamac:rentamac@db:5432/rentamac"

    # WireGuard Gateway
    GATEWAY_IP: str = "89.125.30.138"
    GATEWAY_WG_PORT: int = 51820
    GATEWAY_WG_PUBLIC_KEY: str = ""

    # macOS Node Access
    MAC_ADMIN_USER: str = "admin"
    MAC_SSH_KEY_PATH: str = "/app/.ssh/id_ed25519"

    # YooKassa
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""

    # Crypto
    CRYPTO_WALLET_BTC: str = ""
    CRYPTO_WALLET_USDT_TRC20: str = ""
    CRYPTO_WALLET_USDT_ERC20: str = ""
    CRYPTO_WALLET_ETH: str = ""
    NOWPAYMENTS_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = (
        "https://rentamac.ru,"
        "https://www.rentamac.ru,"
        "https://rentamac.pro,"
        "https://www.rentamac.pro,"
        "http://localhost:3000"
    )

    # RustDesk
    RUSTDESK_SERVER_IP: str = "89.125.30.138"
    RUSTDESK_ID_PORT: int = 21116
    RUSTDESK_RELAY_PORT: int = 21117
    RUSTDESK_KEY: str = "5vfB20zg1GrdIROkejqmvydVIRj4fwXKlH+Zw3mqRGI="

    # Security
    SECRET_KEY: str = "change-me-in-production"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
