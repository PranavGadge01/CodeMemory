"""Unit tests for KnowledgeExporter Markdown output generation."""

from pathlib import Path
import pytest

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.exporters.knowledge_exporter import KnowledgeExporter


def test_exporter_file_structure(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    prob = service.add_problem(
        title="Subsets",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Backtracking"],
        url="https://leetcode.com/problems/subsets/",
        statement="Given an integer array nums of unique elements, return all possible subsets.",
    )

    service.add_submission(
        problem_identifier=prob.slug,
        code="def subsets(nums):\n    res = [[]]\n    for n in nums:\n        res += [r + [n] for r in res]\n    return res",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=35.0,
        memory_mb=16.1,
    )

    exporter = KnowledgeExporter(output_dir=tmp_path / "knowledge")
    exported_paths = exporter.export_all(list(service.list_problems()))

    assert len(exported_paths) == 1
    p_dir = exported_paths[0]
    assert p_dir.exists()

    prob_md = p_dir / "problem.md"
    attempts_md = p_dir / "attempts.md"
    solution_py = p_dir / "solution.py"
    metadata_json = p_dir / "metadata.json"

    assert prob_md.exists()
    assert attempts_md.exists()
    assert solution_py.exists()
    assert metadata_json.exists()

    prob_content = prob_md.read_text(encoding="utf-8")
    assert "Subsets" in prob_content
    assert "`Medium`" in prob_content
    assert "`Array`" in prob_content

    att_content = attempts_md.read_text(encoding="utf-8")
    assert "Attempts History: Subsets" in att_content
    assert "35.0 ms" in att_content

    sol_content = solution_py.read_text(encoding="utf-8")
    assert "def subsets(nums):" in sol_content
