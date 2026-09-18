"""Service for generating solution evolution summaries across multiple attempts."""

from typing import List, Optional
from pydantic import BaseModel
from codememory.ai.base import BaseAIProvider
from codememory.ai.fallback_provider import HeuristicAIProvider
from codememory.domain.models import Problem, Submission


class EvolutionStep(BaseModel):
    """Step in the solution evolution sequence."""

    attempt_number: int
    status: str
    approach: str
    time_complexity: str
    space_complexity: str
    runtime: Optional[str] = None
    memory: Optional[str] = None
    timestamp: str


class EvolutionSummary(BaseModel):
    """Overall solution evolution summary for a problem."""

    problem_id: str
    problem_title: str
    total_attempts: int
    steps: List[EvolutionStep]
    evolution_narrative: str
    key_breakthrough: Optional[str] = None


class EvolutionService:
    """Service to track and construct solution evolution narratives."""

    def __init__(self, ai_provider: Optional[BaseAIProvider] = None):
        self.ai_provider = ai_provider or HeuristicAIProvider()

    def generate_evolution(self, problem: Problem, submissions: List[Submission]) -> EvolutionSummary:
        """Generate a structured evolution timeline and natural language narrative."""
        if not submissions:
            return EvolutionSummary(
                problem_id=problem.id,
                problem_title=problem.title,
                total_attempts=0,
                steps=[],
                evolution_narrative="No submission attempts recorded yet.",
            )

        # Sort chronologically
        sorted_submissions = sorted(submissions, key=lambda s: s.submitted_at)
        steps: List[EvolutionStep] = []

        prev_sub: Optional[Submission] = None
        for idx, sub in enumerate(sorted_submissions, start=1):
            analysis = self.ai_provider.analyze_submission(sub, problem, prev_sub)
            steps.append(
                EvolutionStep(
                    attempt_number=idx,
                    status=sub.status.value,
                    approach=analysis.inferred_approach,
                    time_complexity=analysis.time_complexity,
                    space_complexity=analysis.space_complexity,
                    runtime=f"{sub.runtime_ms:.1f} ms" if sub.runtime_ms is not None else None,
                    memory=f"{sub.memory_mb:.1f} MB" if sub.memory_mb is not None else None,
                    timestamp=sub.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if sub.submitted_at else "N/A",
                )
            )
            prev_sub = sub

        # Formulate natural language narrative
        if len(steps) == 1:
            step = steps[0]
            narrative = f"Solved in 1 attempt using a {step.approach} approach ({step.time_complexity} time, {step.space_complexity} space)."
            breakthrough = f"Directly implemented optimal {step.approach} approach."
        else:
            first_step = steps[0]
            last_step = steps[-1]
            accepted_step = next((s for s in reversed(steps) if s.status == "Accepted"), None)

            target_step = accepted_step or last_step

            if first_step.approach != target_step.approach or first_step.time_complexity != target_step.time_complexity:
                narrative = (
                    f"Your solution evolved across {len(steps)} attempts from a {first_step.approach} ({first_step.time_complexity}) approach "
                    f"to an optimized {target_step.approach} ({target_step.time_complexity}) solution."
                )
                breakthrough = f"Transitioned from {first_step.time_complexity} ({first_step.approach}) to {target_step.time_complexity} ({target_step.approach})."
            else:
                narrative = (
                    f"Maintained a {target_step.approach} ({target_step.time_complexity}) approach across {len(steps)} attempts, "
                    f"refining edge case handling until achieving {target_step.status} status."
                )
                breakthrough = f"Iteratively debugged edge cases and constraints to reach {target_step.status}."

        return EvolutionSummary(
            problem_id=problem.id,
            problem_title=problem.title,
            total_attempts=len(steps),
            steps=steps,
            evolution_narrative=narrative,
            key_breakthrough=breakthrough,
        )
