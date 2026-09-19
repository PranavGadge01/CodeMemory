"""Service for storing and managing local platform account connections securely."""

import json
from pathlib import Path
from typing import Dict, Optional
from pydantic import ValidationError

from codememory.connectors.account.models import AccountConnection, AccountStatus


class AccountService:
    """Manages local account connection metadata and persistence."""

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / "account_connections.json"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create the connection store directory if it is absent.

        The store is created on demand rather than assumed to exist: this
        service is long-lived (it is cached behind the lazy
        ``CodeMemoryService.leetcode`` surface) while the data tree beneath it
        can be rebuilt at any time — the Settings "Clear All Data" action
        removes ``data/`` and recreates only its top level. Recreating the
        directory here keeps a stale service instance persisting connections
        instead of failing with a ``FileNotFoundError`` on write.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> Dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_all(self, data: Dict[str, dict]) -> None:
        self._ensure_dir()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def get_connection(self, provider: str = "LeetCode") -> Optional[AccountConnection]:
        """Retrieve active account connection for provider."""
        all_conns = self._read_all()
        raw = all_conns.get(provider.lower())
        if not raw:
            return None
        try:
            return AccountConnection.model_validate(raw)
        except ValidationError:
            return None

    def save_connection(self, conn: AccountConnection) -> AccountConnection:
        """Save or update an account connection record."""
        all_conns = self._read_all()
        all_conns[conn.provider.lower()] = conn.model_dump(mode="json")
        self._write_all(all_conns)
        return conn

    def remove_connection(self, provider: str = "LeetCode") -> bool:
        """Remove connection metadata for a provider."""
        all_conns = self._read_all()
        if provider.lower() in all_conns:
            all_conns.pop(provider.lower())
            self._write_all(all_conns)
            return True
        return False

    def is_connected(self, provider: str = "LeetCode") -> bool:
        """Check if provider is connected."""
        conn = self.get_connection(provider)
        return bool(conn and conn.status == AccountStatus.CONNECTED)
