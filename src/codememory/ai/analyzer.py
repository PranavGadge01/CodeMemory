"""AI Code Analyzer with caching, versioning, and deterministic submission identity checks."""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
import polars as pl

from codememory.ai.models import SubmissionAnalysis, SolutionEvolution
from codememory.ai.providers.base_provider import BaseAIProvider
from codememory.ai.providers.heuristic_provider import HeuristicAIProvider
from codememory.domain.models import Problem, Submission


def compute_code_hash(submission_id: str, code: str, status_str: str) -> str:
    """Compute deterministic SHA256 code hash for analysis identity caching."""
    raw = f"{submission_id}:{code.strip()}:{status_str.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AICodeAnalyzer:
    """Orchestrates structured submission analysis and solution evolution with caching & versioning."""

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        cache_dir: str | Path = "data",
        analysis_version: str = "v1",
    ):
        self.provider = provider or HeuristicAIProvider()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.parquet_path = self.cache_dir / "ai_analyses.parquet"
        self.evolution_parquet_path = self.cache_dir / "evolution_analyses.parquet"
        self.analysis_version = analysis_version

        # In-memory cache map: (submission_id, code_hash, analysis_version) -> SubmissionAnalysis
        self._analysis_cache: Dict[tuple[str, str, str], SubmissionAnalysis] = {}
        self._evolution_cache: Dict[tuple[str, str], SolutionEvolution] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load stored AI analyses from Parquet disk storage into in-memory cache."""
        if self.parquet_path.exists():
            try:
                df = pl.read_parquet(self.parquet_path)
                for row in df.iter_rows(named=True):
                    sub_id = row["submission_id"]
                    c_hash = row["code_hash"]
                    ver = row["analysis_version"]
                    analysis_dict = json.loads(row["analysis_json"])
                    self._analysis_cache[(sub_id, c_hash, ver)] = SubmissionAnalysis.model_validate(analysis_dict)
            except Exception:
                pass

        if self.evolution_parquet_path.exists():
            try:
                df_evo = pl.read_parquet(self.evolution_parquet_path)
                for row in df_evo.iter_rows(named=True):
                    p_id = row["problem_id"]
                    ver = row["analysis_version"]
                    evo_dict = json.loads(row["evolution_json"])
                    self._evolution_cache[(p_id, ver)] = SolutionEvolution.model_validate(evo_dict)
            except Exception:
                pass

    def _persist_cache(self) -> None:
        """Persist in-memory AI analysis caches to Parquet files."""
        if self._analysis_cache:
            rows = []
            for (sub_id, c_hash, ver), analysis in self._analysis_cache.items():
                rows.append(
                    {
                        "submission_id": sub_id,
                        "code_hash": c_hash,
                        "analysis_version": ver,
                        "analysis_json": json.dumps(analysis.model_dump()),
                    }
                )
            pl.DataFrame(rows).write_parquet(self.parquet_path)

        if self._evolution_cache:
            evo_rows = []
            for (p_id, ver), evo in self._evolution_cache.items():
                evo_rows.append(
                    {
                        "problem_id": p_id,
                        "analysis_version": ver,
                        "evolution_json": json.dumps(evo.model_dump()),
                    }
                )
            pl.DataFrame(evo_rows).write_parquet(self.evolution_parquet_path)

    def analyze_submission(
        self,
        submission: Submission,
        problem: Problem,
        previous_submission: Optional[Submission] = None,
        force_refresh: bool = False,
    ) -> SubmissionAnalysis:
        """Analyze single submission attempt with cache lookup based on submission_id + code_hash + version."""
        status_str = submission.status.value if hasattr(submission.status, "value") else str(submission.status)
        code_hash = compute_code_hash(submission.id, submission.code or "", status_str)
        cache_key = (submission.id, code_hash, self.analysis_version)

        if not force_refresh and cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        # Trigger AI analysis call
        analysis = self.provider.analyze_submission(submission, problem, previous_submission)
        analysis.analysis_version = self.analysis_version

        # Store in cache
        self._analysis_cache[cache_key] = analysis
        self._persist_cache()
        return analysis

    def analyze_evolution(
        self,
        problem: Problem,
        submissions: List[Submission],
        force_refresh: bool = False,
    ) -> SolutionEvolution:
        """Analyze multi-attempt solution evolution with caching."""
        cache_key = (problem.id, self.analysis_version)

        if not force_refresh and cache_key in self._evolution_cache:
            return self._evolution_cache[cache_key]

        evolution = self.provider.analyze_evolution(problem, submissions)
        evolution.analysis_version = self.analysis_version

        self._evolution_cache[cache_key] = evolution
        self._persist_cache()
        return evolution
