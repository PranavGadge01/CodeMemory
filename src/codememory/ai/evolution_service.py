"""Service for generating solution evolution summaries across multiple attempts."""

from typing import List, Optional
from pydantic import BaseModel, Field
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
    better_approach: Optional[str] = None
    similar_problems: List[str] = Field(default_factory=list)


SIMILAR_PROBLEMS_CATALOG: dict[str, list[str]] = {
    "two-sum": ["3Sum", "Two Sum II - Input Array Is Sorted", "Subarray Sum Equals K"],
    "3sum": ["4Sum", "3Sum Closest", "Two Sum"],
    "climbing-stairs": ["Min Cost Climbing Stairs", "House Robber", "Fibonacci Number"],
    "min-cost-climbing-stairs": ["Climbing Stairs", "House Robber", "Coin Change"],
    "reverse-linked-list": ["Reverse Linked List II", "Palindrome Linked List", "Swap Nodes in Pairs"],
    "lru-cache": ["LFU Cache", "Design InMemory File System", "Insert Delete GetRandom O(1)"],
    "binary-tree-level-order-traversal": ["Binary Tree Zigzag Level Order Traversal", "Binary Tree Right Side View", "Populating Next Right Pointers in Each Node"],
    "longest-substring-without-repeating-characters": ["Minimum Window Substring", "Longest Repeating Character Replacement", "Substrings with Concatenation of All Words"],
    "container-with-most-water": ["Trapping Rain Water", "3Sum", "Two Sum II - Input Array Is Sorted"],
    "valid-parentheses": ["Generate Parentheses", "Longest Valid Parentheses", "Simplify Path"],
    "merge-two-sorted-lists": ["Merge k Sorted Lists", "Sort List", "Merge Sorted Array"],
    "maximum-subarray": ["Maximum Product Subarray", "Degree of an Array", "Best Time to Buy and Sell Stock"],
    "search-in-rotated-sorted-array": ["Find Minimum in Rotated Sorted Array", "Search in Rotated Sorted Array II", "Search Insert Position"],
    "coin-change": ["Coin Change II", "Combination Sum IV", "House Robber"],
    "number-of-islands": ["Max Area of Island", "Surrounded Regions", "Number of Closed Islands"],
    "course-schedule": ["Course Schedule II", "Alien Dictionary", "Minimum Height Trees"],
    "word-break": ["Word Break II", "Concatenated Words", "Extra Characters in a String"],
    "kth-largest-element-in-an-array": ["Top K Frequent Elements", "Kth Largest Element in a Stream", "Find K Pairs with Smallest Sums"],
    "subsets": ["Subsets II", "Permutations", "Combination Sum"],
    "trapping-rain-water": ["Container With Most Water", "Trapping Rain Water II", "Product of Array Except Self"],
}

TOPIC_SIMILAR_FALLBACKS: dict[str, list[str]] = {
    "dynamic programming": ["Coin Change", "House Robber", "Longest Common Subsequence"],
    "hash table": ["Two Sum", "Group Anagrams", "Subarray Sum Equals K"],
    "array": ["Two Sum", "Maximum Subarray", "3Sum"],
    "string": ["Valid Anagram", "Longest Substring Without Repeating Characters", "Group Anagrams"],
    "tree": ["Binary Tree Inorder Traversal", "Maximum Depth of Binary Tree", "Invert Binary Tree"],
    "graph": ["Number of Islands", "Course Schedule", "Clone Graph"],
    "linked list": ["Reverse Linked List", "Merge Two Sorted Lists", "Linked List Cycle"],
    "two pointers": ["Two Sum II", "3Sum", "Container With Most Water"],
    "sliding window": ["Longest Substring Without Repeating Characters", "Minimum Window Substring", "Sliding Window Maximum"],
    "binary search": ["Binary Search", "Search in Rotated Sorted Array", "Find First and Last Position"],
}


def _derive_better_approach(problem: Problem, steps: List[EvolutionStep]) -> str:
    """Generate optimal approach advice based on latest attempt and problem metadata."""
    if not steps:
        return "Implement an initial working solution, starting with brute force or direct simulation to verify correctness."
    
    last_step = steps[-1]
    topics_lower = [t.lower() for t in (problem.topics or [])]
    
    if "o(n^2)" in last_step.time_complexity.lower() or "o(2^n)" in last_step.time_complexity.lower():
        if any(t in topics_lower for t in ["hash table", "array"]):
            return "Use a Hash Map or Frequency Table to trade O(N) auxiliary space for O(N) linear time, eliminating quadratic nested loops."
        if any(t in topics_lower for t in ["dynamic programming", "recursion"]):
            return "Apply Dynamic Programming with memoization or tabulation to eliminate redundant overlapping subproblems and achieve linear runtime."
        return "Optimize runtime complexity to O(N) or O(N log N) using sorting, two pointers, or balanced data structures."

    if any(t in topics_lower for t in ["dynamic programming", "memoization"]):
        return "Transition top-down memoization to bottom-up DP with state compression to reduce space complexity to O(1) auxiliary space."

    if any(t in topics_lower for t in ["tree", "graph", "depth-first search"]):
        return "Use an iterative stack or queue approach to avoid potential call-stack overflow on deep tree/graph structures."

    return f"Optimize {last_step.approach} by using in-place operations and early-exit conditions to reduce constant factor overhead."


def _derive_similar_problems(problem: Problem) -> List[str]:
    slug = (problem.slug or "").lower()
    if slug in SIMILAR_PROBLEMS_CATALOG:
        return SIMILAR_PROBLEMS_CATALOG[slug]
    
    for t in (problem.topics or []):
        t_lower = t.lower()
        if t_lower in TOPIC_SIMILAR_FALLBACKS:
            return [p for p in TOPIC_SIMILAR_FALLBACKS[t_lower] if p.lower() != problem.title.lower()][:3]
            
    return ["Two Sum", "Climbing Stairs", "Reverse Linked List"]


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
                better_approach=_derive_better_approach(problem, []),
                similar_problems=_derive_similar_problems(problem),
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

        better_app = _derive_better_approach(problem, steps)
        similar_probs = _derive_similar_problems(problem)

        return EvolutionSummary(
            problem_id=problem.id,
            problem_title=problem.title,
            total_attempts=len(steps),
            steps=steps,
            evolution_narrative=narrative,
            key_breakthrough=breakthrough,
            better_approach=better_app,
            similar_problems=similar_probs,
        )
