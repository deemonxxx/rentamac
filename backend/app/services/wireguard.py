"""WireGuard management service — key generation, IP allocation, config rendering."""

from __future__ import annotations

import ipaddress
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

# WireGuard subnet for client-to-gateway communication
WG_SUBNET = ipaddress.IPv4Network("10.66.66.0/24")
GATEWAY_WG_IP = "10.66.66.1"
CLIENT_IP_PREFIX = "10.66.66."


class WireGuardManager:
    """Manages WireGuard key pairs, IP allocation, and config generation.

    Client traffic flows: Client → Gateway (this server) → Mac Node
    The gateway acts as a WireGuard hub.
    """

    def __init__(self, template_dir: Optional[Path] = None) -> None:
        self.template_dir = template_dir or TEMPLATE_DIR
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            keep_trailing_newline=True,
        )

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate a WireGuard private/public key pair.

        Returns:
            Tuple of (private_key, public_key) as base64 strings.

        Raises:
            RuntimeError: If key generation fails.
        """
        try:
            private_key = subprocess.check_output(
                ["wg", "genkey"],
                text=True,
                stderr=subprocess.PIPE,
            ).strip()
            public_key = subprocess.check_output(
                ["wg", "pubkey"],
                input=private_key + "\n",
                text=True,
                stderr=subprocess.PIPE,
            ).strip()
            return private_key, public_key
        except FileNotFoundError:
            logger.warning("wg binary not found, generating placeholder keys")
            import base64, os
            raw_priv = os.urandom(32)
            # In production, wg must be installed. This is a fallback for development.
            priv_b64 = base64.b64encode(raw_priv).decode()
            pub_b64 = base64.b64encode(os.urandom(32)).decode()
            return priv_b64, pub_b64
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"WireGuard key generation failed: {exc.stderr}") from exc

    @staticmethod
    def generate_psk() -> str:
        """Generate a WireGuard preshared key.

        Returns:
            Base64-encoded preshared key string.
        """
        try:
            return subprocess.check_output(
                ["wg", "genpsk"],
                text=True,
                stderr=subprocess.PIPE,
            ).strip()
        except FileNotFoundError:
            import base64, os
            return base64.b64encode(os.urandom(32)).decode()
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"WireGuard PSK generation failed: {exc.stderr}") from exc

    def next_client_ip(self, existing_ips: List[str]) -> str:
        """Allocate the next available WireGuard IP for a client.

        Scans existing IPs and returns the next unused address in the 10.66.66.0/24 range.
        Starts at 10.66.66.2 (10.66.66.1 is the gateway).

        Args:
            existing_ips: List of already-assigned IP strings.

        Returns:
            Next available IP as a string (e.g., "10.66.66.2").

        Raises:
            RuntimeError: If no IPs are available.
        """
        used = set()
        for ip_str in existing_ips:
            if ip_str:
                used.add(ipaddress.IPv4Address(ip_str))

        # Start from .2 (.1 is the gateway)
        for host in WG_SUBNET.hosts():
            if host == ipaddress.IPv4Address(GATEWAY_WG_IP):
                continue
            if host not in used:
                return str(host)

        raise RuntimeError("No available WireGuard IPs in subnet")

    def render_client_config(
        self,
        client_private_key: str,
        client_ip: str,
        dns: str = "1.1.1.1",
    ) -> str:
        """Render a WireGuard client configuration from the Jinja2 template.

        Args:
            client_private_key: The client's WireGuard private key.
            client_ip: The client's WireGuard IP (e.g., "10.66.66.2").
            dns: DNS server to use.

        Returns:
            Rendered WireGuard configuration file content.
        """
        template = self._jinja_env.get_template("wg_client.conf.j2")
        return template.render(
            client_private_key=client_private_key,
            client_ip=client_ip,
            gateway_endpoint=f"{settings.GATEWAY_IP}:{settings.GATEWAY_WG_PORT}",
            gateway_public_key=settings.GATEWAY_WG_PUBLIC_KEY,
            dns=dns,
        )

    def render_gateway_peer_block(
        self,
        client_public_key: str,
        client_ip: str,
        allowed_ips: Optional[str] = None,
    ) -> str:
        """Generate a WireGuard [Peer] block to add to the gateway config.

        Args:
            client_public_key: The client's WireGuard public key.
            client_ip: The client's WireGuard IP.
            allowed_ips: Override allowed IPs (default: client_ip/32).

        Returns:
            String containing the [Peer] configuration block.
        """
        effective_allowed = allowed_ips or f"{client_ip}/32"
        return (
            f"[Peer]\n"
            f"PublicKey = {client_public_key}\n"
            f"AllowedIPs = {effective_allowed}\n"
        )
