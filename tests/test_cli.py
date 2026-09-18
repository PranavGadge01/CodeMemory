"""Unit tests for CodeMemory CLI commands."""

import json
from pathlib import Path
import pytest

from codememory.cli.main import build_parser, main


def test_cli_parser_help():
    parser = build_parser()
    assert parser.prog == "codememory"


def test_cli_seed_and_list(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["seed"])
    main(["list"])
    main(["stats"])
    main(["export"])


def test_cli_import_and_problem(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data = [
        {
            "title": "Min Cost Climbing Stairs",
            "difficulty": "Easy",
            "language": "python",
            "code": "def minCostClimbingStairs(cost): pass",
            "status": "Accepted",
            "runtime": "42 ms",
            "memory": "16.0 MB",
        }
    ]
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data), encoding="utf-8")

    main(["import", str(f)])
    main(["problem", "min-cost-climbing-stairs"])
    main(["history", "min-cost-climbing-stairs"])
