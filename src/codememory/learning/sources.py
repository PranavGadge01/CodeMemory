"""Verified problem sources for candidate retrieval.

There is exactly one problem-source abstraction.  A *local* source reads the
user's own stored problems; a *remote* source reads real, published LeetCode
metadata through the existing :class:`LeetCodeClient` transport (no second
integration).  The remote source is cached and bounded, falls back to local on
any failure, and never runs unless it is explicitly enabled -- so an ordinary
page load never depends on a network round-trip.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Protocol, Sequence

from codememory.domain.models import Problem
from codememory.learning.models import ProblemCandidate

logger = logging.getLogger(__name__)

_LEETCODE_URL_TEMPLATE = "https://leetcode.com/problems/{slug}/"


class ProblemSource(Protocol):
    """A read-only provider of real problem candidates."""

    name: str

    def list_candidates(self) -> list[ProblemCandidate]:
        """Return candidate problems. Must never raise; return [] on failure."""
        ...


# ---------------------------------------------------------------------------
# Local catalogue
# ---------------------------------------------------------------------------


class LocalCatalogSource:
    """Source backed by the user's own stored problems.

    This is the only source guaranteed to be available offline.  It never
    invents metadata: a problem without a URL produces a candidate with
    ``url=None``.
    """

    name = "local_catalog"

    def __init__(self, storage) -> None:
        self._storage = storage

    def list_candidates(self) -> list[ProblemCandidate]:
        try:
            problems = list(self._storage.list_all())
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Local catalog read failed: %s", exc)
            return []
        return [local_problem_to_candidate(p) for p in problems]


def local_problem_to_candidate(problem: Problem) -> ProblemCandidate:
    """Normalise a stored :class:`Problem` into a :class:`ProblemCandidate`."""
    difficulty = getattr(problem.difficulty, "value", problem.difficulty)
    return ProblemCandidate(
        problem_id=problem.id,
        slug=problem.slug or "",
        title=problem.title or "",
        difficulty=str(difficulty) if difficulty else "Unknown",
        topics=list(problem.topics or []),
        url=problem.url or None,
        source="local_catalog",
        metadata_complete=bool(problem.title and problem.slug),
    )


# ---------------------------------------------------------------------------
# Remote LeetCode catalogue (cached)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemoteSourceConfig:
    """Configuration for the cached remote problem source."""

    enabled: bool = False
    ttl_seconds: int = 24 * 60 * 60
    limit: int = 200


def remote_source_config_from_env() -> RemoteSourceConfig:
    """Read remote-source configuration from the environment.

    ``CODEMEMORY_PROBLEM_SOURCE`` controls behaviour:
      * ``local``    -- never touch the network (default for tests/CI).
      * ``auto``     -- use a fresh cache if present; otherwise try once and
                        fall back silently to local on failure.
      * ``leetcode`` -- same as ``auto`` but logs remote failures loudly.
    """
    mode = (os.environ.get("CODEMEMORY_PROBLEM_SOURCE") or "local").strip().lower()
    enabled = mode in {"auto", "leetcode", "remote"}
    try:
        ttl = int(os.environ.get("CODEMEMORY_PROBLEM_CACHE_TTL", str(24 * 60 * 60)))
    except ValueError:
        ttl = 24 * 60 * 60
    try:
        limit = int(os.environ.get("CODEMEMORY_REMOTE_PROBLEM_LIMIT", "200"))
    except ValueError:
        limit = 200
    return RemoteSourceConfig(enabled=enabled, ttl_seconds=max(0, ttl), limit=max(1, limit))


class LeetCodeProblemSource:
    """Cached, bounded source of real LeetCode problem metadata.

    The source uses the repository's existing LeetCode GraphQL client.  Results
    are cached on disk with a TTL and memoised in-process, so the network is
    touched at most once per TTL window rather than once per request.
    """

    name = "leetcode"

    def __init__(
        self,
        client,
        cache_path: str | Path,
        config: Optional[RemoteSourceConfig] = None,
    ) -> None:
        self._client = client
        self._cache_path = Path(cache_path)
        self._config = config or RemoteSourceConfig(enabled=True)
        self._memo: list[ProblemCandidate] | None = None

    # -- public API ------------------------------------------------------

    def list_candidates(self) -> list[ProblemCandidate]:
        if self._memo is not None:
            return self._memo

        cached = self._read_cache()
        if cached is not None:
            self._memo = cached
            return cached

        if not self._config.enabled:
            self._memo = []
            return []

        fetched = self._fetch()
        if fetched:
            self._write_cache(fetched)
            self._memo = fetched
            return fetched

        # Remote unavailable: do not repeat the attempt in this process.
        self._memo = []
        return []

    # -- internals -------------------------------------------------------

    def _read_cache(self) -> list[ProblemCandidate] | None:
        if self._config.ttl_seconds <= 0:
            return None
        try:
            if not self._cache_path.exists():
                return None
            raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
            fetched_at = float(raw.get("fetched_at", 0))
            if time.time() - fetched_at > self._config.ttl_seconds:
                return None
            items = raw.get("problems")
            if not isinstance(items, list):
                return None
            candidates = [ProblemCandidate.model_validate(item) for item in items]
            return [c for c in candidates if c.metadata_complete]
        except Exception as exc:  # noqa: BLE001 - cache must never break a request
            logger.debug("Problem catalogue cache unreadable: %s", exc)
            return None

    def _write_cache(self, candidates: Sequence[ProblemCandidate]) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "fetched_at": time.time(),
                "problems": [c.model_dump() for c in candidates],
            }
            tmp = self._cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.replace(self._cache_path)
        except Exception as exc:  # noqa: BLE001 - caching is best-effort
            logger.debug("Problem catalogue cache write failed: %s", exc)

    def _fetch(self) -> list[ProblemCandidate]:
        fetch = getattr(self._client, "fetch_problem_list", None)
        if fetch is None:
            return []
        try:
            raw_items = fetch(limit=self._config.limit) or []
        except Exception as exc:  # noqa: BLE001 - network must never break a request
            logger.info("LeetCode problem catalogue fetch failed: %s", exc)
            return []

        candidates: list[ProblemCandidate] = []
        for item in raw_items:
            candidate = self._normalise(item)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _normalise(self, item) -> ProblemCandidate | None:
        slug = (getattr(item, "title_slug", None) or "").strip()
        title = (getattr(item, "title", None) or "").strip()
        if not slug or not title:
            return None
        difficulty = (getattr(item, "difficulty", None) or "Unknown").strip() or "Unknown"
        topics = [t for t in (getattr(item, "topics", None) or []) if t]
        problem_id = str(getattr(item, "question_id", None) or getattr(item, "id", None) or slug)
        url = getattr(item, "url", None) or _LEETCODE_URL_TEMPLATE.format(slug=slug)
        return ProblemCandidate(
            problem_id=problem_id,
            slug=slug,
            title=title,
            difficulty=difficulty,
            topics=topics,
            url=url,
            source="leetcode",
            premium_only=bool(getattr(item, "is_paid_only", False)),
            metadata_complete=True,
        )


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------


class CompositeProblemSource:
    """Merge several sources, de-duplicating by canonical identity.

    Sources are consulted in order; the first occurrence of a canonical key
    wins, so local catalogue metadata (which may carry the user's own recorded
    URL) is preferred over a remote duplicate.
    """

    name = "composite"

    def __init__(self, sources: Sequence[ProblemSource]) -> None:
        self._sources = [s for s in sources if s is not None]

    def list_candidates(self) -> list[ProblemCandidate]:
        merged: list[ProblemCandidate] = []
        seen: set[str] = set()
        for source in self._sources:
            try:
                items = source.list_candidates()
            except Exception as exc:  # noqa: BLE001 - a source failure is not fatal
                logger.warning("Problem source %r failed: %s", getattr(source, "name", source), exc)
                continue
            for candidate in items:
                key = candidate.key
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(candidate)
        return merged


def build_problem_source(storage, base_dir: str | Path, client=None) -> ProblemSource:
    """Build the default problem source for a service instance.

    Local catalogue is always available.  The remote source is layered on only
    when enabled by configuration; when disabled (the default) the returned
    source is local-only and never performs network I/O.
    """
    sources: list[ProblemSource] = [LocalCatalogSource(storage)]
    config = remote_source_config_from_env()
    if config.enabled:
        try:
            if client is None:
                from codememory.connectors.leetcode.client import LeetCodeClient

                client = LeetCodeClient()
            sources.append(
                LeetCodeProblemSource(
                    client=client,
                    cache_path=Path(base_dir) / "problem_catalog_cache.json",
                    config=config,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Remote problem source unavailable: %s", exc)
    return CompositeProblemSource(sources)


def candidates_from_problems(problems: Iterable[Problem]) -> list[ProblemCandidate]:
    """Convenience helper converting stored problems to candidates."""
    return [local_problem_to_candidate(p) for p in problems]
