"""Unit tests for personal InsightsGenerator."""

from pathlib import Path
import pytest

from codememory.analytics.insights import InsightsGenerator
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, SubmissionStatus


def test_insights_generation(tmp_path: Path):
    service = CodeMemoryService(
        base_dir=tmp_path / "data",
        knowledge_dir=tmp_path / "knowledge",
        db_path=tmp_path / "data" / "test.duckdb",
    )

    # Empty insights check
    empty_insights = service.generate_insights()
    assert len(empty_insights) == 1
    assert "No coding problems" in empty_insights[0]

    # Seed data insights check
    from scripts.seed_data import seed_sample_data
    seed_sample_data(service)

    insights = service.generate_insights()
    assert len(insights) > 1
    assert any("Primary programming language" in ins or "Python" in ins for ins in insights)
