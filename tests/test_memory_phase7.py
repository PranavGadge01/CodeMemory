"""Comprehensive unit & E2E tests for Phase 7 Semantic Personal Memory Engine."""

from pathlib import Path
import pytest

from codememory.ai.analyzer import AICodeAnalyzer
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.cli.main import build_parser, main as cli_main
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem, Submission
from codememory.memory.embeddings import LocalEmbeddingProvider, MockEmbeddingProvider
from codememory.memory.index import SemanticIndex, cosine_similarity
from codememory.memory.models import MemoryDocument, MemoryType, compute_content_hash
from codememory.memory.pipeline import DocumentPipeline
from codememory.memory.retriever import HybridRetriever
from codememory.memory.service import MemoryService


def test_embedding_provider_dimensionality_and_vectors():
    local_provider = LocalEmbeddingProvider(dimension=64)
    assert local_provider.dimension == 64
    vec1 = local_provider.embed("sliding window algorithm")
    assert len(vec1) == 64

    vec2 = local_provider.embed("sliding window algorithm")
    assert vec1 == vec2  # Deterministic

    vec3 = local_provider.embed("graph breadth first search")
    sim_same = cosine_similarity(vec1, vec2)
    sim_diff = cosine_similarity(vec1, vec3)
    assert sim_same == pytest.approx(1.0, abs=1e-3)
    assert sim_diff < 0.9  # Distinct topics produce distinct vectors


def test_semantic_index_persistence_and_search(tmp_path: Path):
    index = SemanticIndex(data_dir=tmp_path, embedding_version="v1")
    assert index.count() == 0

    doc1 = MemoryDocument(
        memory_id="m1",
        memory_type=MemoryType.PROBLEM,
        problem_id="p1",
        title="Two Sum",
        content="HashMap lookup for complement",
    )
    doc2 = MemoryDocument(
        memory_id="m2",
        memory_type=MemoryType.PROBLEM,
        problem_id="p2",
        title="Binary Search",
        content="Divide and conquer logarithmic search",
    )

    vec1 = [1.0] + [0.0] * 31
    vec2 = [0.0, 1.0] + [0.0] * 30

    index.add(doc1, vec1)
    index.add(doc2, vec2)
    index.save()

    assert index.count() == 2
    assert index.is_indexed("m1", doc1.content_hash)

    # Search with vector close to vec1
    query_vec = [0.9, 0.1] + [0.0] * 30
    results = index.search(query_vec, top_k=2)
    assert len(results) == 2
    assert results[0][0] == "m1"  # Highest similarity to m1


def test_document_pipeline_provenance_extraction():
    pipeline = DocumentPipeline()
    p = Problem(
        title="Valid Anagram",
        slug="valid-anagram",
        difficulty=DifficultyLevel.EASY,
        topics=["Hash Table", "String"],
    )
    sub = Submission(
        problem_id=p.id,
        code="def isAnagram(s, t):\n return sorted(s) == sorted(t)",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=35.0,
    )
    from codememory.domain.models import Attempt
    att = Attempt(problem_id=p.id, attempt_number=1, approach_summary="Sorting", status=SubmissionStatus.ACCEPTED, submissions=[sub])
    p.attempts.append(att)

    docs = pipeline.extract_documents([p])
    assert len(docs) >= 3  # Problem metadata, Attempt, Submission

    prob_doc = next(d for d in docs if d.memory_type == MemoryType.PROBLEM)
    assert prob_doc.title == "Valid Anagram"
    assert prob_doc.source_reference["problem_id"] == p.id

    sub_doc = next(d for d in docs if d.memory_type == MemoryType.SUBMISSION)
    assert sub_doc.submission_id == sub.id
    assert sub_doc.source_reference["submission_id"] == sub.id


def test_incremental_indexing_skips_unchanged_documents(tmp_path: Path):
    db_path = tmp_path / "test_inc.duckdb"
    service = CodeMemoryService(base_dir=tmp_path, knowledge_dir=tmp_path / "knowledge", db_path=db_path)

    service.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array"])
    service.add_submission("two-sum", code="def twoSum(): pass", status=SubmissionStatus.ACCEPTED)

    # Initial index run
    res1 = service.memory_engine.index_all(force_rebuild=False)
    assert res1["indexed"] > 0
    assert res1["skipped"] == 0

    # Second index run without changes -> should skip all
    res2 = service.memory_engine.index_all(force_rebuild=False)
    assert res2["indexed"] == 0
    assert res2["skipped"] == res1["total_documents"]


def test_e2e_two_sum_and_longest_substring_scenario(tmp_path: Path):
    db_path = tmp_path / "test_e2e.duckdb"
    service = CodeMemoryService(base_dir=tmp_path, knowledge_dir=tmp_path / "knowledge", db_path=db_path)

    # 1. Problem: Two Sum
    service.add_problem(title="Two Sum", slug="two-sum", difficulty=DifficultyLevel.EASY, topics=["Array", "Hash Table"])
    service.add_submission(
        "two-sum",
        code="def twoSum(nums, target):\n for i in range(len(nums)):\n  for j in range(i+1, len(nums)):\n   if nums[i]+nums[j]==target: return [i,j]",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        "two-sum",
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target], i]\n  hashmap[n] = i",
        language="python",
        status=SubmissionStatus.WRONG_ANSWER,
    )
    service.add_submission(
        "two-sum",
        code="def twoSum(nums, target):\n hashmap = {}\n for i, n in enumerate(nums):\n  if target - n in hashmap: return [hashmap[target - n], i]\n  hashmap[n] = i",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=45.0,
    )

    # 2. Problem: Longest Substring Without Repeating Characters
    service.add_problem(title="Longest Substring Without Repeating Characters", slug="longest-substring", difficulty=DifficultyLevel.MEDIUM, topics=["Hash Table", "String", "Sliding Window"])
    service.add_submission(
        "longest-substring",
        code="def lengthOfLongestSubstring(s):\n for i in range(len(s)):\n  for j in range(i, len(s)):\n   if len(set(s[i:j])) != j-i: pass",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
    )
    service.add_submission(
        "longest-substring",
        code="def lengthOfLongestSubstring(s):\n char_map = {}\n left = max_len = 0\n for right, char in enumerate(s):\n  if char in char_map and char_map[char] >= left: left = char_map[char] + 1\n  char_map[char] = right\n  max_len = max(max_len, right - left + 1)\n return max_len",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=55.0,
    )

    # Run Indexing
    service.memory_engine.index_all()

    # Search: "problems where I used brute force and got TLE"
    search_tle = service.memory_engine.search("problems where I used brute force and got TLE", top_k=10)
    assert len(search_tle) >= 2
    titles_tle = [s.title for s in search_tle]
    assert any("Two Sum" in t for t in titles_tle)
    assert any("Longest Substring" in t for t in titles_tle)

    # Similar problems to Two Sum
    similar = service.memory_engine.find_similar_problem("two-sum", top_k=2)
    assert len(similar) > 0
    assert similar[0].title == "Longest Substring Without Repeating Characters"
    assert "shared topics: hash table" in similar[0].explanation.lower()

    # Historical Mistakes
    mistakes = service.memory_engine.find_common_mistakes()
    assert len(mistakes) > 0
    assert any("Time Limit Exceeded" in m.content or "TLE" in m.content or "Wrong Answer" in m.content for m in mistakes)

    # Solution Evolution
    history = service.memory_engine.find_previous_approaches("two-sum")
    assert len(history) == 3
    assert history[0]["status"] == "Time Limit Exceeded"
    assert history[1]["status"] == "Wrong Answer"
    assert history[2]["status"] == "Accepted"


def test_cli_memory_commands(tmp_path: Path, monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["memory", "stats"])
    assert args.command == "memory"
    assert args.action == "stats"
