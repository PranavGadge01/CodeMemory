"""Regression tests for the on-disk lifetime of the account-connection store.

The connection store lives at ``<base_dir>/accounts/account_connections.json``
and is owned by an :class:`AccountService` that stays alive for the whole
process behind the lazy ``CodeMemoryService.leetcode`` surface. The data tree
beneath it can be rebuilt at any moment — the Settings "Clear All Data" action
removes ``data/`` and recreates only its top level — so the store directory has
to be (re)created when a connection is persisted, not only when the service was
built.

Before that was handled at write time, the mismatch surfaced in the UI as

    [Errno 2] No such file or directory:
    'data\\accounts\\account_connections.json'

the moment a valid username was submitted after the data tree had been cleared.
Every test here drives the real ``service.leetcode`` surface with the LeetCode
transport mocked, so none of them touches the network.
"""

import json
from pathlib import Path

import pytest

from codememory.connectors.account.models import AccountStatus
from codememory.connectors.account.service import AccountService
from codememory.core.service import CodeMemoryService

_USERNAME = "jaypatil1229"

_PROFILE = {
    "real_name": "Jay Patil",
    "user_avatar": "https://leetcode.com/a.png",
    "ranking": 1234,
    "solved_all": 42,
    "solved_easy": 20,
    "solved_medium": 15,
    "solved_hard": 7,
}


def _make_service(tmp_path: Path, **overrides) -> CodeMemoryService:
    """A service whose whole data tree lives under ``tmp_path``."""
    kwargs = {
        "base_dir": tmp_path / "data",
        "knowledge_dir": tmp_path / "knowledge",
        "db_path": tmp_path / "data" / "codememory.duckdb",
    }
    kwargs.update(overrides)
    return CodeMemoryService(**kwargs)


@pytest.fixture
def mocked_profile(monkeypatch):
    """Answer a public profile lookup for any username, without the network.

    ``CodeMemoryService.leetcode`` builds its own client, so the public API is
    stubbed on the client class rather than injected.
    """

    def _fetch_user_profile(self, username: str) -> dict:
        return {**_PROFILE, "username": username}

    monkeypatch.setattr(
        "codememory.connectors.leetcode.client.LeetCodeClient.fetch_user_profile",
        _fetch_user_profile,
    )


# ─────────────────────────────────────────────────────────────────────────────
# The reported failure: connect after the data tree was rebuilt
# ─────────────────────────────────────────────────────────────────────────────


def _clear_data_tree_like_settings(base_dir: Path) -> None:
    """Reproduce what the Settings "Clear All Data" action leaves behind.

    It removes the whole data directory and recreates only its top level, so
    every subdirectory underneath — including the account store — is gone.
    """
    if base_dir.exists():
        import shutil

        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)


def test_connect_after_data_tree_cleared(tmp_path, mocked_profile):
    """A valid username connects even when the store directory was removed.

    This is the exact reported scenario: the cached ``service.leetcode`` surface
    outlives the data tree it was built against, and connecting must rebuild the
    store rather than raise ``[Errno 2] No such file or directory``.
    """
    service = _make_service(tmp_path)
    leetcode = service.leetcode  # lazy Phase C surface; builds data/accounts
    account_file = Path(leetcode._account_service.file_path)
    assert account_file.parent.is_dir()

    _clear_data_tree_like_settings(service.base_dir)
    assert not account_file.parent.exists(), "the store directory is gone"

    conn = leetcode.connect(_USERNAME)

    assert conn.username == _USERNAME
    assert conn.status == AccountStatus.CONNECTED
    # The store was recreated where the configured base_dir says it belongs.
    assert account_file.is_file()
    stored = json.loads(account_file.read_text(encoding="utf-8"))
    assert stored["leetcode"]["username"] == _USERNAME

    # A fresh process reading the same base_dir sees the same connection, so the
    # persisted state really is durable rather than in-memory only.
    reopened = _make_service(tmp_path).leetcode
    assert reopened.is_connected()
    assert reopened.status().username == _USERNAME


def test_connect_into_fresh_data_dir(tmp_path, mocked_profile):
    """Connecting into an untouched data tree creates the store on demand."""
    service = _make_service(tmp_path)
    account_file = Path(service.leetcode._account_service.file_path)

    conn = service.leetcode.connect(_USERNAME)

    assert conn.status == AccountStatus.CONNECTED
    assert account_file.is_file()
    assert service.leetcode.is_connected()


def test_status_reads_cleanly_when_store_directory_is_absent(tmp_path, mocked_profile):
    """A missing store reports "not connected" instead of raising."""
    service = _make_service(tmp_path)
    _clear_data_tree_like_settings(service.base_dir)

    status = service.leetcode.status()

    assert not status.connected
    assert status.username is None
    assert not service.leetcode.is_connected()


# ─────────────────────────────────────────────────────────────────────────────
# The configured base_dir must own the store location
# ─────────────────────────────────────────────────────────────────────────────


def test_store_follows_configured_base_dir(tmp_path, mocked_profile, monkeypatch):
    """The connection store lands under the configured base_dir and nowhere else."""
    custom = tmp_path / "elsewhere"
    monkeypatch.chdir(tmp_path)  # so the default relative "data" would be visible
    service = _make_service(tmp_path, base_dir=custom)

    account_file = Path(service.leetcode._account_service.file_path)
    assert account_file == custom / "accounts" / "account_connections.json"

    service.leetcode.connect(_USERNAME)

    assert account_file.is_file()
    # The default location was not silently used as a fallback.
    assert not (tmp_path / "data" / "accounts").exists()


def test_store_path_is_derived_not_hardcoded(tmp_path, monkeypatch):
    """No absolute path is baked into the surface; it always tracks base_dir."""
    monkeypatch.chdir(tmp_path)
    service = CodeMemoryService(base_dir="custom", knowledge_dir="knowledge", db_path="custom/db.duckdb")

    account_service = service.leetcode._account_service

    # Derived from the configured base_dir, never from a fixed literal.
    assert account_service.data_dir == service.base_dir / "accounts"
    assert account_service.file_path == service.base_dir / "accounts" / "account_connections.json"
    assert not account_service.file_path.is_absolute()
    assert account_service.file_path.parts[-2:] == ("accounts", "account_connections.json")


# ─────────────────────────────────────────────────────────────────────────────
# AccountService directly — behaviour shared by every account provider
# ─────────────────────────────────────────────────────────────────────────────


def test_account_service_recreates_removed_directory_on_save(tmp_path):
    """A store directory removed after construction is rebuilt on the next write."""
    account_service = AccountService(data_dir=tmp_path / "accounts")
    account_service.data_dir.rmdir()

    conn = account_service.save_connection(
        _provider_connection()
    )

    assert conn.provider == "LeetCode"
    assert (tmp_path / "accounts" / "account_connections.json").is_file()


def test_account_service_reads_missing_directory_as_empty(tmp_path):
    """Reading from a directory that no longer exists yields no connection."""
    account_service = AccountService(data_dir=tmp_path / "accounts")
    account_service.data_dir.rmdir()

    assert account_service.get_connection("LeetCode") is None
    assert account_service.is_connected("LeetCode") is False


def test_account_service_preserves_other_providers(tmp_path):
    """Recreating the store directory never disturbs another provider's record."""
    account_service = AccountService(data_dir=tmp_path / "accounts")
    account_service.save_connection(_provider_connection(provider="Codeforces"))

    account_service.save_connection(_provider_connection())

    assert account_service.get_connection("Codeforces") is not None
    assert account_service.get_connection("Codeforces").provider == "Codeforces"
    assert account_service.get_connection("LeetCode").username == _USERNAME


def _provider_connection(provider: str = "LeetCode"):
    from datetime import datetime, timezone

    from codememory.connectors.account.models import AccountConnection

    return AccountConnection(
        provider=provider,
        username=_USERNAME,
        display_name=_USERNAME,
        status=AccountStatus.CONNECTED,
        connected_at=datetime.now(timezone.utc),
    )
