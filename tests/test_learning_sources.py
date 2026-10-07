"""Unit tests for the verified problem sources.

Covers remote LeetCode metadata normalisation, disk caching with TTL,
environment-driven configuration, composite de-duplication and the offline
default.  These tests never touch the network: the LeetCode transport is
replaced by a small deterministic fake.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from codememory.connectors.leetcode.models import LeetCodeProblemRaw
from codememory.domain.enums import DifficultyLevel
from codememory.domain.models import Problem
from codememory.learning.models import ProblemCandidate
from codememory.learning.sources import (
    CompositeProblemSource,
    LeetCodeProblemSource,
    LocalCatalogSource,
    RemoteSourceConfig,
    build_problem_source,
    local_problem_to_candidate,
    remote_source_config_from_env,
)


def _raw(**kwargs) -> LeetCodeProblemRaw:
    payload = {"title": "Sample", "title_slug": "sample"}
    payload.update(kwargs)
    return LeetCodeProblemRaw(**payload)


class _StaticRemoteClient:
    """Fake LeetCode transport returning a fixed problem list."""

    def __init__(self, items):
        self._items = list(items)
        self.calls = 0
        self.last_limit = None

    def fetch_problem_list(self, limit=200):
        self.calls += 1
        self.last_limit = limit
        return list(self._items)


class _NoFetchClient:
    """A client without the catalogue method (older stub)."""


class _FailingClient:
    def fetch_problem_list(self, limit=200):
        raise RuntimeError("network unavailable")


class _ExplodingStorage:
    def list_all(self):
        raise RuntimeError("storage offline")


@pytest.fixture()
def workdir():
    # Workspace-local temp dir: the sandbox denies pytest's default %TEMP%.
    with tempfile.TemporaryDirectory(dir=".") as tmp:
        yield Path(tmp)


def _cache_path(workdir: Path) -> Path:
    return workdir / "problem_catalog_cache.json"


# ---------------------------------------------------------------------------
# Configuration parsing
# ---------------------------------------------------------------------------


class TestRemoteConfig:
    def test_defaults_to_local_and_disabled(self, monkeypatch):
        for name in (
            "CODEMEMORY_PROBLEM_SOURCE",
            "CODEMEMORY_PROBLEM_CACHE_TTL",
            "CODEMEMORY_REMOTE_PROBLEM_LIMIT",
        ):
            monkeypatch.delenv(name, raising=False)
        config = remote_source_config_from_env()
        assert config.enabled is False
        assert config.ttl_seconds == 24 * 60 * 60
        assert config.limit == 200

    @pytest.mark.parametrize("mode", ["auto", "leetcode", "remote", "AUTO"])
    def test_remote_modes_enable_source(self, monkeypatch, mode):
        monkeypatch.setenv("CODEMEMORY_PROBLEM_SOURCE", mode)
        assert remote_source_config_from_env().enabled is True

    def test_local_mode_stays_disabled(self, monkeypatch):
        monkeypatch.setenv("CODEMEMORY_PROBLEM_SOURCE", "local")
        assert remote_source_config_from_env().enabled is False

    def test_invalid_env_values_fall_back_to_defaults(self, monkeypatch):
        monkeypatch.setenv("CODEMEMORY_PROBLEM_CACHE_TTL", "not-a-number")
        monkeypatch.setenv("CODEMEMORY_REMOTE_PROBLEM_LIMIT", "many")
        config = remote_source_config_from_env()
        assert config.ttl_seconds == 24 * 60 * 60
        assert config.limit == 200

    def test_env_values_are_clamped(self, monkeypatch):
        monkeypatch.setenv("CODEMEMORY_PROBLEM_CACHE_TTL", "-5")
        monkeypatch.setenv("CODEMEMORY_REMOTE_PROBLEM_LIMIT", "0")
        config = remote_source_config_from_env()
        assert config.ttl_seconds == 0
        assert config.limit == 1


# ---------------------------------------------------------------------------
# Remote normalisation
# ---------------------------------------------------------------------------


class TestRemoteNormalisation:
    def test_public_metadata_is_normalised(self, workdir):
        client = _StaticRemoteClient(
            [
                _raw(
                    question_id="1",
                    title="Two Sum",
                    title_slug="two-sum",
                    difficulty="Easy",
                    topics=["Array", "Hash Table"],
                ),
                _raw(
                    question_id="167",
                    title="Two Sum II",
                    title_slug="two-sum-ii-input-array-is-sorted",
                    difficulty="Medium",
                    topics=["Array", "Two Pointers", "Binary Search"],
                    is_paid_only=True,
                ),
            ]
        )
        source = LeetCodeProblemSource(
            client=client, cache_path=_cache_path(workdir), config=RemoteSourceConfig(enabled=True)
        )
        candidates = source.list_candidates()
        assert [c.slug for c in candidates] == ["two-sum", "two-sum-ii-input-array-is-sorted"]
        first = candidates[0]
        assert first.title == "Two Sum"
        assert first.difficulty == "Easy"
        assert first.topics == ["Array", "Hash Table"]
        assert first.url == "https://leetcode.com/problems/two-sum/"
        assert first.source == "leetcode"
        assert first.premium_only is False
        assert first.metadata_complete is True
        assert candidates[1].premium_only is True
        assert candidates[1].topics == ["Array", "Two Pointers", "Binary Search"]

    def test_explicit_url_is_preserved(self, workdir):
        client = _StaticRemoteClient(
            [_raw(question_id="1", title="Two Sum", title_slug="two-sum", url="https://example.test/two-sum")]
        )
        source = LeetCodeProblemSource(
            client=client, cache_path=_cache_path(workdir), config=RemoteSourceConfig(enabled=True)
        )
        assert source.list_candidates()[0].url == "https://example.test/two-sum"

    def test_entries_missing_identity_are_dropped(self, workdir):
        client = _StaticRemoteClient(
            [
                _raw(title="", title_slug=""),
                _raw(title="No Slug", title_slug=""),
                _raw(title="Ok", title_slug="ok"),
            ]
        )
        source = LeetCodeProblemSource(
            client=client, cache_path=_cache_path(workdir), config=RemoteSourceConfig(enabled=True)
        )
        assert [c.slug for c in source.list_candidates()] == ["ok"]

    def test_configured_limit_is_forwarded(self, workdir):
        client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        source = LeetCodeProblemSource(
            client=client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, limit=42),
        )
        source.list_candidates()
        assert client.last_limit == 42


# ---------------------------------------------------------------------------
# Remote caching
# ---------------------------------------------------------------------------


class TestRemoteCaching:
    def test_fetch_writes_cache_and_is_memoised(self, workdir):
        client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        source = LeetCodeProblemSource(
            client=client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, ttl_seconds=3600),
        )
        assert [c.slug for c in source.list_candidates()] == ["ok"]
        assert client.calls == 1
        assert _cache_path(workdir).exists()
        # Second call within the same instance must not refetch.
        source.list_candidates()
        assert client.calls == 1

    def test_fresh_cache_is_reused_without_network(self, workdir):
        first_client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        LeetCodeProblemSource(
            client=first_client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, ttl_seconds=3600),
        ).list_candidates()

        second_client = _StaticRemoteClient([])
        reader = LeetCodeProblemSource(
            client=second_client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, ttl_seconds=3600),
        )
        assert [c.slug for c in reader.list_candidates()] == ["ok"]
        assert second_client.calls == 0

    def test_expired_cache_triggers_refetch(self, workdir):
        cache = _cache_path(workdir)
        cache.write_text(
            json.dumps(
                {
                    "fetched_at": time.time() - 7200,
                    "problems": [
                        ProblemCandidate(
                            problem_id="1", slug="stale", title="Stale", difficulty="Easy"
                        ).model_dump()
                    ],
                }
            ),
            encoding="utf-8",
        )
        client = _StaticRemoteClient([_raw(question_id="2", title="Fresh", title_slug="fresh")])
        source = LeetCodeProblemSource(
            client=client,
            cache_path=cache,
            config=RemoteSourceConfig(enabled=True, ttl_seconds=60),
        )
        assert [c.slug for c in source.list_candidates()] == ["fresh"]
        assert client.calls == 1

    def test_corrupt_cache_is_ignored(self, workdir):
        cache = _cache_path(workdir)
        cache.write_text("{ not valid json", encoding="utf-8")
        client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        source = LeetCodeProblemSource(
            client=client,
            cache_path=cache,
            config=RemoteSourceConfig(enabled=True, ttl_seconds=3600),
        )
        assert [c.slug for c in source.list_candidates()] == ["ok"]
        assert client.calls == 1

    def test_ttl_zero_disables_cache_reads(self, workdir):
        first_client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        LeetCodeProblemSource(
            client=first_client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, ttl_seconds=3600),
        ).list_candidates()
        second_client = _StaticRemoteClient([_raw(title="Other", title_slug="other")])
        source = LeetCodeProblemSource(
            client=second_client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True, ttl_seconds=0),
        )
        assert [c.slug for c in source.list_candidates()] == ["other"]
        assert second_client.calls == 1


# ---------------------------------------------------------------------------
# Remote failure / offline behaviour
# ---------------------------------------------------------------------------


class TestRemoteFailureHandling:
    def test_disabled_source_never_calls_client(self, workdir):
        client = _StaticRemoteClient([_raw(title="Ok", title_slug="ok")])
        source = LeetCodeProblemSource(
            client=client,
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=False),
        )
        assert source.list_candidates() == []
        assert client.calls == 0

    def test_network_failure_returns_empty_and_memoises(self, workdir):
        source = LeetCodeProblemSource(
            client=_FailingClient(),
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True),
        )
        assert source.list_candidates() == []
        # A failure must not be retried on every subsequent call.
        assert source.list_candidates() == []

    def test_client_without_catalogue_method_returns_empty(self, workdir):
        source = LeetCodeProblemSource(
            client=_NoFetchClient(),
            cache_path=_cache_path(workdir),
            config=RemoteSourceConfig(enabled=True),
        )
        assert source.list_candidates() == []

    def test_build_problem_source_is_local_only_by_default(self, monkeypatch, workdir):
        monkeypatch.delenv("CODEMEMORY_PROBLEM_SOURCE", raising=False)
        storage = _FakeStorage(
            [
                Problem(
                    id="two-sum",
                    title="Two Sum",
                    slug="two-sum",
                    difficulty=DifficultyLevel.EASY,
                    platform="LeetCode",
                    topics=["Array"],
                    url="https://leetcode.com/problems/two-sum/",
                )
            ]
        )
        source = build_problem_source(storage, workdir)
        assert source.name == "composite"
        assert [c.slug for c in source.list_candidates()] == ["two-sum"]


class _FakeStorage:
    def __init__(self, problems):
        self._problems = list(problems)

    def list_all(self):
        return list(self._problems)


# ---------------------------------------------------------------------------
# Local catalogue
# ---------------------------------------------------------------------------


class TestLocalCatalog:
    def test_local_problem_without_url_is_honest(self):
        problem = Problem(
            id="p1",
            title="Local Only",
            slug="local-only",
            difficulty=DifficultyLevel.MEDIUM,
            platform="LeetCode",
            topics=["Array"],
        )
        candidate = local_problem_to_candidate(problem)
        assert candidate.url is None
        assert candidate.source == "local_catalog"
        assert candidate.difficulty == "Medium"
        assert candidate.metadata_complete is True

    def test_local_source_survives_storage_failure(self):
        assert LocalCatalogSource(_ExplodingStorage()).list_candidates() == []

    def test_composite_prefers_local_metadata(self):
        local = LocalCatalogSource(
            _FakeStorage(
                [
                    Problem(
                        id="two-sum",
                        title="Two Sum",
                        slug="two-sum",
                        difficulty=DifficultyLevel.EASY,
                        platform="LeetCode",
                        topics=["Array"],
                        url="https://local.test/two-sum",
                    )
                ]
            )
        )
        remote = _StaticSource(
            [
                ProblemCandidate(
                    problem_id="1",
                    slug="two-sum",
                    title="Two Sum",
                    difficulty="Easy",
                    topics=["Array"],
                    source="leetcode",
                    url="https://leetcode.com/problems/two-sum/",
                ),
                ProblemCandidate(
                    problem_id="2",
                    slug="add-two-numbers",
                    title="Add Two Numbers",
                    difficulty="Medium",
                    topics=["Linked List"],
                    source="leetcode",
                ),
            ]
        )
        merged = CompositeProblemSource([local, remote]).list_candidates()
        assert [c.key for c in merged] == ["two-sum", "add-two-numbers"]
        assert merged[0].source == "local_catalog"
        assert merged[0].url == "https://local.test/two-sum"


class _StaticSource:
    def __init__(self, candidates):
        self._candidates = list(candidates)

    def list_candidates(self):
        return list(self._candidates)
