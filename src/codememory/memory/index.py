"""Lightweight local semantic index for memory document vectors."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import polars as pl

from codememory.memory.models import MemoryDocument


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math_sqrt = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticIndex:
    """Persisted, incremental semantic vector index backed by Parquet storage."""

    def __init__(self, data_dir: str | Path = "data", embedding_version: str = "v1"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.parquet_path = self.data_dir / "memory_embeddings.parquet"
        self.embedding_version = embedding_version

        # In-memory index structures:
        # memory_id -> {content_hash, embedding_version, indexed_at, vector, doc_meta}
        self._index: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        """Load stored vectors and metadata from Parquet file."""
        if not self.parquet_path.exists():
            return
        try:
            df = pl.read_parquet(self.parquet_path)
            for row in df.iter_rows(named=True):
                m_id = row["memory_id"]
                vec = json.loads(row["vector_json"])
                self._index[m_id] = {
                    "memory_id": m_id,
                    "content_hash": row["content_hash"],
                    "embedding_version": row["embedding_version"],
                    "indexed_at": row["indexed_at"],
                    "vector": vec,
                    "problem_id": row.get("problem_id", ""),
                    "memory_type": row.get("memory_type", ""),
                    "title": row.get("title", ""),
                    "source_provider": row.get("source_provider", ""),
                    "source_account": row.get("source_account", ""),
                }
        except Exception:
            pass

    def _persist(self) -> None:
        """Persist in-memory vectors to Parquet file."""
        if not self._index:
            if self.parquet_path.exists():
                try:
                    self.parquet_path.unlink()
                except Exception:
                    pass
            return

        rows = []
        for m_id, data in self._index.items():
            rows.append(
                {
                    "memory_id": m_id,
                    "problem_id": data.get("problem_id", ""),
                    "memory_type": data.get("memory_type", ""),
                    "title": data.get("title", ""),
                    "content_hash": data["content_hash"],
                    "embedding_version": data["embedding_version"],
                    "indexed_at": data["indexed_at"],
                    "vector_json": json.dumps(data["vector"]),
                    "source_provider": data.get("source_provider", ""),
                    "source_account": data.get("source_account", ""),
                }
            )
        pl.DataFrame(rows).write_parquet(self.parquet_path)

    def is_indexed(self, memory_id: str, content_hash: str) -> bool:
        """Check if memory item is already indexed with matching content hash & version."""
        if memory_id not in self._index:
            return False
        entry = self._index[memory_id]
        return (
            entry["content_hash"] == content_hash
            and entry["embedding_version"] == self.embedding_version
        )

    def add(self, doc: MemoryDocument, vector: List[float]) -> None:
        """Add or update a memory document vector in the index."""
        self._index[doc.memory_id] = {
            "memory_id": doc.memory_id,
            "problem_id": doc.problem_id,
            "memory_type": doc.memory_type.value,
            "title": doc.title,
            "content_hash": doc.content_hash,
            "embedding_version": self.embedding_version,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "vector": vector,
            "source_provider": doc.source_provider or "",
            "source_account": doc.source_account or "",
        }

    def save(self) -> None:
        """Explicitly persist changes to Parquet."""
        self._persist()

    def count(self) -> int:
        """Return total number of vectors in index."""
        return len(self._index)

    def search(self, query_vector: List[float], top_k: int = 10, account: str | None = None) -> List[Tuple[str, float]]:
        """Search top-K memory IDs by cosine similarity against query vector.

        When ``account`` is provided, only documents whose ``source_account``
        matches are considered. When ``account`` is None, documents with no
        ``source_account`` (legacy/manual) are still returned alongside any
        that happen to have no account set — but in practice the caller
        (MemoryService) is responsible for ensuring LeetCode-sourced docs are
        not exposed cross-account.
        """
        if not self._index or not query_vector:
            return []

        scores: List[Tuple[str, float]] = []
        for m_id, data in self._index.items():
            if account is not None:
                doc_account = data.get("source_account", "")
                if doc_account != account:
                    continue
            sim = cosine_similarity(query_vector, data["vector"])
            scores.append((m_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def clear(self) -> None:
        """Clear all entries from index."""
        self._index.clear()
        self._persist()
