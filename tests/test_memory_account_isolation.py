"""Test suite for Memory Account Isolation (Phase 8 hardening)."""
import os
import pytest
from pathlib import Path

from codememory.memory.models import MemoryType, MemoryDocument
from codememory.memory.service import MemoryService
from codememory.memory.pipeline import DocumentPipeline
from codememory.memory.index import SemanticIndex
from codememory.memory.retriever import HybridRetriever
from codememory.memory.embeddings import MockEmbeddingProvider
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus, Platform
from codememory.domain.models import Problem, Attempt, Submission
from codememory.storage.duckdb_repository import DuckDBStorage


@pytest.fixture
def tmp_codememory(tmp_path):
    base_dir = str(tmp_path / "data")
    knowledge_dir = str(tmp_path / "knowledge")
    db_path = str(tmp_path / "test.duckdb")
    service = CodeMemoryService(
        base_dir=base_dir,
        knowledge_dir=knowledge_dir,
        db_path=db_path,
    )
    yield service
    service.close_storage()


def set_active_account(monkeypatch, account):
    """Helper to set active_account via monkeypatch (auto-restored)."""
    monkeypatch.setattr(CodeMemoryService, "active_account", property(lambda s: account))


class TestMemoryAccountIsolation:
    def test_search_isolated_by_account(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_a")
        results_a = tmp_codememory.memory_search("two-sum")
        for r in results_a:
            assert r.source_account == "account_a"

        set_active_account(monkeypatch, "account_b")
        results_b = tmp_codememory.memory_search("two-sum")
        for r in results_b:
            assert r.source_account == "account_b"

    def test_search_without_account_returns_empty(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, None)
        results = tmp_codememory.memory_search("two-sum")
        assert results == []


class TestFindSimilarProblemIsolation:
    def test_find_similar_problem_excludes_other_accounts(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
        prob_a, _ = tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        prob_b = Problem(id="prob-b", title="Two Sum B", slug="two-sum-b", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"], platform=Platform.LEETCODE)
        Attempt(problem_id=prob_b.id, attempt_number=1, approach_summary="Brute force", status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
        tmp_codememory.storage.save(prob_b)
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_a")
        similar_a = tmp_codememory.memory_find_similar_problem(prob_a.id)
        for doc in similar_a:
            assert doc.source_account == "account_a"


class TestFindCommonMistakesIsolation:
    def test_find_common_mistakes_isolated_by_account(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")

        prob_b = Problem(id="prob-b-2", title="Reverse String", slug="reverse-string", difficulty=DifficultyLevel.EASY, topics=["String"], platform=Platform.LEETCODE)
        Attempt(problem_id=prob_b.id, attempt_number=1, mistakes=["Timeout error"], status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
        tmp_codememory.storage.save(prob_b)
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_a")
        mistakes_a = tmp_codememory.memory_find_common_mistakes()
        for doc in mistakes_a:
            assert doc.source_account == "account_a"

        set_active_account(monkeypatch, "account_b")
        mistakes_b = tmp_codememory.memory_find_common_mistakes()
        for doc in mistakes_b:
            assert doc.source_account == "account_b"

        ids_a = {d.memory_id for d in mistakes_a}
        ids_b = {d.memory_id for d in mistakes_b}
        assert ids_a.isdisjoint(ids_b)


class TestFindPreviousApproachesIsolation:
    def test_find_previous_approaches_isolated_by_account(self, tmp_codememory, monkeypatch):
        prob_a = tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")

        prob_b = Problem(id="prob-b-3", title="Two Sum B", slug="two-sum-b", difficulty=DifficultyLevel.EASY, topics=["Array"], platform=Platform.LEETCODE)
        att_b = Attempt(problem_id=prob_b.id, attempt_number=1, approach_summary="Hash map approach", status=SubmissionStatus.ACCEPTED)
        att_b.submissions.append(Submission(problem_id=prob_b.id, code="def twoSum(): pass", language="python", status=SubmissionStatus.ACCEPTED, source_provider="leetcode", source_account="account_b"))
        prob_b.attempts.append(att_b)
        tmp_codememory.storage.save(prob_b)
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_a")
        approaches_a = tmp_codememory.memory_find_previous_approaches(prob_a.id)
        assert len(approaches_a) > 0

        set_active_account(monkeypatch, "account_b")
        approaches_b = tmp_codememory.memory_find_previous_approaches(prob_b.id)
        assert len(approaches_b) > 0


class TestMemoryStatsIsolation:
    def test_memory_stats_counts_only_account_documents(self, tmp_codememory, monkeypatch):
        # Account A problems + submissions
        tmp_codememory.add_problem(title="A1", slug="a1", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("a1", code="x", status=SubmissionStatus.ACCEPTED,
                                       source_provider="leetcode", source_account="account_a")
        tmp_codememory.add_problem(title="A2", slug="a2", difficulty=DifficultyLevel.MEDIUM, topics=["String"])
        tmp_codememory.add_submission("a2", code="y", status=SubmissionStatus.WRONG_ANSWER,
                                       source_provider="leetcode", source_account="account_a")

        # Account B problem + submission
        prob_b = Problem(id="pb1", title="B1", slug="b1", difficulty=DifficultyLevel.HARD, topics=["Graph"], platform=Platform.LEETCODE)
        att_b = Attempt(problem_id=prob_b.id, attempt_number=1, approach_summary="Graph approach", status=SubmissionStatus.ACCEPTED)
        att_b.submissions.append(Submission(
            problem_id=prob_b.id, code="z", language="python",
            status=SubmissionStatus.ACCEPTED,
            source_provider="leetcode", source_account="account_b",
        ))
        prob_b.attempts.append(att_b)
        tmp_codememory.storage.save(prob_b)

        # Index as account A
        set_active_account(monkeypatch, "account_a")
        tmp_codememory.memory_index_all()
        stats_a = tmp_codememory.memory_stats()

        # Clear cache and re-index as account B
        set_active_account(monkeypatch, "account_b")
        tmp_codememory.memory_engine._doc_cache = []
        tmp_codememory.memory_engine._doc_map = {}
        tmp_codememory.memory_index_all(force_rebuild=True)
        stats_b = tmp_codememory.memory_stats()

        assert stats_a["total_documents"] > 0, "Account A has no memory documents"
        assert stats_b["total_documents"] > 0, "Account B has no memory documents"


class TestMemoryDocumentProvenance:
    def test_memory_document_has_source_fields(self):
        doc = MemoryDocument(memory_id="m1", memory_type=MemoryType.PROBLEM, problem_id="p1", title="Two Sum", content="HashMap approach", source_provider="leetcode", source_account="account_a")
        assert hasattr(doc, "source_provider")
        assert hasattr(doc, "source_account")
        assert doc.source_provider == "leetcode"
        assert doc.source_account == "account_a"


class TestDocumentPipelineProvenance:
    def test_pipeline_propagates_source_account(self):
        pipeline = DocumentPipeline()
        problem = Problem(title="Valid Anagram", slug="valid-anagram", difficulty=DifficultyLevel.EASY, topics=["Hash Table", "String"], platform=Platform.LEETCODE)
        attempt = Attempt(problem_id=problem.id, attempt_number=1, approach_summary="Sorting approach", status=SubmissionStatus.ACCEPTED)
        attempt.submissions.append(Submission(problem_id=problem.id, code="def solve(): pass", language="python", status=SubmissionStatus.ACCEPTED, source_provider="leetcode", source_account="account_a"))
        problem.attempts.append(attempt)

        docs = pipeline.extract_documents([problem])

        prob_docs = [d for d in docs if d.memory_type == MemoryType.PROBLEM]
        for doc in prob_docs:
            assert doc.source_provider == "leetcode"
            assert doc.source_account == "account_a"


class TestSemanticIndexAccountFilter:
    def test_semantic_index_search_filters_by_account(self, tmp_path):
        index = SemanticIndex(data_dir=str(tmp_path / "memory"))
        provider = MockEmbeddingProvider(dimension=32)

        doc_a = MemoryDocument(memory_id="doc-a", memory_type=MemoryType.MISTAKE, problem_id="p1", title="Two Sum Mistake", content="set seen values", source_provider="leetcode", source_account="account_a")
        index.add(doc_a, provider.embed("mistake set seen"))

        doc_b = MemoryDocument(memory_id="doc-b", memory_type=MemoryType.MISTAKE, problem_id="p2", title="Reverse String Mistake", content="pointer manipulation", source_provider="leetcode", source_account="account_b")
        index.add(doc_b, provider.embed("mistake pointer manipulation"))
        index.save()

        retriever = HybridRetriever(index=index, embedding_provider=provider)
        docs = [doc_a, doc_b]
        results_a = retriever.search(query="set seen values", documents=docs, account="account_a", top_k=10)
        for doc in results_a:
            assert doc.source_account == "account_a"

        results_b = retriever.search(query="pointer manipulation", documents=docs, account="account_b", top_k=10)
        for doc in results_b:
            assert doc.source_account == "account_b"


class TestHybridRetrieverAccountFilter:
    def test_hybrid_retriever_filters_by_account(self, tmp_path):
        index = SemanticIndex(data_dir=str(tmp_path / "memory"))
        provider = MockEmbeddingProvider(dimension=32)

        doc_a = MemoryDocument(memory_id="doc-a-2", memory_type=MemoryType.ATTEMPT, problem_id="p1", title="Two Sum Attempt", content="brute force", source_provider="leetcode", source_account="account_a")
        index.add(doc_a, provider.embed("brute force"))

        doc_b = MemoryDocument(memory_id="doc-b-2", memory_type=MemoryType.ATTEMPT, problem_id="p2", title="Reverse String Attempt", content="recursion technique", source_provider="leetcode", source_account="account_b")
        index.add(doc_b, provider.embed("recursion"))
        index.save()

        retriever = HybridRetriever(index=index, embedding_provider=provider)
        docs = [doc_a, doc_b]
        results_a = retriever.search(query="brute force", documents=docs, account="account_a", top_k=10)
        for doc in results_a:
            assert doc.source_account == "account_a"


class TestMemoryEngineUnscopedMode:
    def test_memory_engine_accepts_none_account(self, tmp_codememory):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        results = tmp_codememory.memory_engine.search(query="two-sum", top_k=10, account=None)
        assert results == []


# --- Tests 11-12: Global search Knowledge section ---


class TestGlobalSearchKnowledgeSection:
    def test_global_search_includes_knowledge_section(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Sliding Window Problem", slug="sliding-window", difficulty=DifficultyLevel.MEDIUM, topics=["Sliding Window"])
        tmp_codememory.add_submission("sliding-window", code="def solve(): pass", status=SubmissionStatus.ACCEPTED, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_a")
        results = tmp_codememory.global_search("sliding window")
        knowledge_hits = [r for r in results if r.get("_type") == "knowledge"]

        assert len(knowledge_hits) > 0, "Knowledge section should contain results for lexical match"
        for hit in knowledge_hits:
            assert hit.get("metadata", {}).get("sourceAccount") == "account_a"


class TestGlobalSearchKnowledgeAccountFilter:
    def test_global_search_knowledge_does_not_leak_accounts(self, tmp_codememory, monkeypatch):
        tmp_codememory.add_problem(title="Sliding Window Problem", slug="sliding-window", difficulty=DifficultyLevel.MEDIUM, topics=["Sliding Window"])
        tmp_codememory.add_submission("sliding-window", code="def solve(): pass", status=SubmissionStatus.ACCEPTED, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        set_active_account(monkeypatch, "account_b")
        results = tmp_codememory.global_search("sliding window")
        knowledge_hits = [r for r in results if r.get("_type") == "knowledge"]

        for hit in knowledge_hits:
            assert hit.get("metadata", {}).get("sourceAccount") != "account_a", "Account A knowledge doc leaked"


# --- Test 13: DuckDB connection lifecycle ---


class TestDuckDBConnectionLifecycle:
    def test_duckdb_close_is_idempotent(self, tmp_path):
        storage = DuckDBStorage(db_path=str(tmp_path / "test_lifecycle.duckdb"))
        storage.close()
        storage.close()

    def test_duckdb_del_does_not_close_shared_connection(self, tmp_path):
        storage = DuckDBStorage(db_path=str(tmp_path / "test_lifecycle2.duckdb"))
        storage.__del__()

    def test_concurrent_reads_same_connection(self, tmp_codememory):
        tmp_codememory.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
        tmp_codememory.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.WRONG_ANSWER, source_provider="leetcode", source_account="account_a")
        tmp_codememory.memory_index_all()

        r1 = tmp_codememory.search_service.search("two-sum")
        r2 = tmp_codememory.search_service.search("two")

    def test_duckdb_close_unregisters_from_global_registry(self, tmp_path):
        db_path = str(tmp_path / "test_reg.duckdb")
        storage1 = DuckDBStorage(db_path=db_path, shared=True)
        storage1.close()

        import codememory.storage.duckdb_repository as mod
        assert db_path not in mod._shared_duckdb_connections
