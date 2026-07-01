"""SSH provisioning service for macOS nodes using paramiko."""

from __future__ import annotations

import logging
import shlex
from typing import Optional

import paramiko

from app.config import settings

logger = logging.getLogger(__name__)


class MacNodeSSH:
    """Manages SSH connections and commands to a macOS node.

    Usage::

        ssh = MacNodeSSH(host="192.168.1.100")
        try:
            ssh.create_user("client_42")
            output = ssh.run_command("whoami")
        finally:
            ssh.close()
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        key_path: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username or settings.MAC_ADMIN_USER
        self.key_path = key_path or settings.MAC_SSH_KEY_PATH
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def _connect(self) -> paramiko.SSHClient:
        """Establish SSH connection if not already connected."""
        if self._client is not None:
            return self._client

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = paramiko.Ed25519Key.from_private_key_file(self.key_path)
        client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            pkey=pkey,
            timeout=self.timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        self._client = client
        logger.info("SSH connected to %s@%s:%d", self.username, self.host, self.port)
        return client

    def run_command(self, command: str, check: bool = True) -> str:
        """Execute a command on the remote macOS node.

        Args:
            command: Shell command string to execute.
            check: If True, raise on non-zero exit code.

        Returns:
            Combined stdout output as a string.

        Raises:
            RuntimeError: If check=True and the command exits with non-zero code.
        """
        client = self._connect()
        logger.debug("Running on %s: %s", self.host, command)
        stdin, stdout, stderr = client.exec_command(command, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()

        if check and exit_code != 0:
            logger.error("Command failed (exit %d): %s\nstderr: %s", exit_code, command, err)
            raise RuntimeError(f"Command failed with exit code {exit_code}: {err}")

        if err:
            logger.debug("stderr: %s", err)

        return out

    def create_user(self, username: str, shell: str = "/bin/zsh") -> None:
        """Create a new user on the macOS node.

        Creates the user with a home directory, sets up SSH directory,
        and generates an authorized_keys file.

        Args:
            username: The username to create.
            shell: Login shell for the user.
        """
        safe_user = shlex.quote(username)
        safe_shell = shlex.quote(shell)

        # Create user with sysadminctl (macOS native)
        commands = [
            f"sudo sysadminctl -addUser {safe_user} -shell {safe_shell} -home /Users/{safe_user} -password '*' 2>&1 || true",
            f"sudo mkdir -p /Users/{safe_user}/.ssh",
            f"sudo chmod 700 /Users/{safe_user}/.ssh",
            f"sudo touch /Users/{safe_user}/.ssh/authorized_keys",
            f"sudo chmod 600 /Users/{safe_user}/.ssh/authorized_keys",
            f"sudo chown -R {safe_user}:staff /Users/{safe_user}",
        ]

        for cmd in commands:
            self.run_command(cmd)

        logger.info("Created user '%s' on %s", username, self.host)

    def delete_user(self, username: str, delete_home: bool = True) -> None:
        """Delete a user from the macOS node.

        Args:
            username: The username to delete.
            delete_home: Whether to also remove the home directory.
        """
        safe_user = shlex.quote(username)
        flag = "-deleteHome" if delete_home else ""
        self.run_command(f"sudo sysadminctl -deleteUser {safe_user} {flag} 2>&1 || true")
        logger.info("Deleted user '%s' from %s", username, self.host)

    def add_ssh_key(self, username: str, public_key: str) -> None:
        """Add an SSH public key to a user's authorized_keys.

        Args:
            username: Target user.
            public_key: The SSH public key string (ssh-ed25519 AAAA...).
        """
        safe_user = shlex.quote(username)
        safe_key = shlex.quote(public_key.strip())
        self.run_command(
            f"echo {safe_key} | sudo tee -a /Users/{safe_user}/.ssh/authorized_keys > /dev/null"
        )
        logger.info("Added SSH key for '%s' on %s", username, self.host)

    def install_wireguard_config(self, config_content: str, config_name: str = "wg0") -> None:
        """Write a WireGuard configuration file and bring up the interface.

        Args:
            config_content: Full WireGuard config file content.
            config_name: Interface name (default wg0).
        """
        safe_name = shlex.quote(config_name)
        # Write config
        self.run_command(f"sudo mkdir -p /etc/wireguard")
        # Use base64 to safely transfer multi-line config
        import base64
        encoded = base64.b64encode(config_content.encode()).decode()
        self.run_command(f"echo '{encoded}' | base64 -d | sudo tee /etc/wireguard/{safe_name}.conf > /dev/null")
        self.run_command(f"sudo chmod 600 /etc/wireguard/{safe_name}.conf")
        # Bring up the interface
        self.run_command(f"sudo wg-quick up {safe_name} 2>&1 || true")
        logger.info("Installed WireGuard config '%s' on %s", config_name, self.host)

    def set_rustdesk_password(self, password: str) -> None:
        """Set a permanent RustDesk password on the macOS node.

        Args:
            password: The permanent password to set.
        """
        safe_pw = shlex.quote(password)
        config_dir = "Library/Preferences/com.carriez.RustDesk"
        self.run_command(
            f"cd ~/{config_dir} && "
            f"sed -i '' 's/^password = .*/password = {safe_pw}/' RustDesk.toml"
        )
        # Restart RustDesk to apply
        self.run_command("pkill -f RustDesk 2>/dev/null || true", check=False)
        import time
        time.sleep(3)
        self.run_command("open -a RustDesk 2>/dev/null || true", check=False)
        logger.info("Set RustDesk password on %s", self.host)

    def get_rustdesk_id(self) -> str:
        """Get the RustDesk ID from the macOS node.

        Returns:
            The RustDesk ID as a string, or empty string if not found.
        """
        try:
            output = self.run_command(
                "cat ~/Library/Preferences/com.carriez.RustDesk/RustDesk2.toml "
                "| grep '^id = ' | cut -d\\\"'\\\" -f2 2>/dev/null || echo ''",
                check=False,
            )
            return output.strip().strip("'\"")
        except Exception:
            return ""

    def clear_rustdesk_password(self) -> None:
        """Clear RustDesk password — next restart will generate a new temp password."""
        config_dir = "Library/Preferences/com.carriez.RustDesk"
        self.run_command(
            f"cd ~/{config_dir} && "
            f"sed -i '' 's/^password = .*/password = \"\"/' RustDesk.toml",
            check=False,
        )
        self.run_command("pkill -f RustDesk 2>/dev/null || true", check=False)
        import time
        time.sleep(3)
        self.run_command("open -a RustDesk 2>/dev/null || true", check=False)
        logger.info("Cleared RustDesk password on %s", self.host)

    def cleanup_client_data(self) -> None:
        """Clean up client data between rentals.

        Removes browser data, downloads, desktop files, caches,
        keychain, and shell history. Does NOT delete the user account.
        """
        cmds = [
            "rm -rf ~/Downloads/* 2>/dev/null || true",
            "rm -rf ~/Desktop/* 2>/dev/null || true",
            "rm -rf ~/Documents/* 2>/dev/null || true",
            "rm -rf ~/.Trash/* 2>/dev/null || true",
            "rm -rf ~/Library/Caches/* 2>/dev/null || true",
            "rm -rf ~/Library/Safari/* 2>/dev/null || true",
            "rm -rf ~/Library/Application\\ Support/Google/Chrome/Default/* 2>/dev/null || true",
            "rm -f ~/.zsh_history ~/.bash_history 2>/dev/null || true",
        ]
        for cmd in cmds:
            self.run_command(cmd, check=False)
        logger.info("Cleaned up client data on %s", self.host)

    def reboot(self) -> None:
        """Reboot the macOS node."""
        self.run_command("sudo shutdown -r now", check=False)
        logger.info("Reboot command sent to %s", self.host)

    def get_system_info(self) -> dict[str, str]:
        """Collect basic system information from the node.

        Returns:
            Dict with keys: hostname, model, macos_version, uptime, cpu, memory.
        """
        info: dict[str, str] = {}
        commands = {
            "hostname": "hostname",
            "model": "sysctl -n hw.model",
            "macos_version": "sw_vers -productVersion",
            "uptime": "uptime",
            "cpu": "sysctl -n machdep.cpu.brand_string",
            "memory": "sysctl -n hw.memsize",
        }
        for key, cmd in commands.items():
            try:
                info[key] = self.run_command(cmd)
            except Exception:
                info[key] = "unknown"

        # Convert memory from bytes to GB
        try:
            mem_bytes = int(info.get("memory", "0"))
            info["memory"] = f"{mem_bytes / (1024 ** 3):.0f} GB"
        except (ValueError, ZeroDivisionError):
            pass

        return info

    def close(self) -> None:
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.debug("SSH connection to %s closed", self.host)

    def __enter__(self) -> "MacNodeSSH":
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.close()
