"""Deterministic structural signals extracted from recorded source code.

These signals describe *what the code text contains* (loop nesting, data
structures used, whether recursion appears) and a conservative complexity
estimate derived from that structure.  They are the deterministic inputs the
learning-insight layer reasons over; nothing here is model-generated.

Every estimate carries a ``basis`` string explaining how it was derived, so the
UI can label it as an estimate rather than a measured fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Ordered from cheapest to most expensive; used to compare attempts.
_COMPLEXITY_RANK: dict[str, int] = {
    "o(1)": 0,
    "o(log n)": 1,
    "o(n)": 2,
    "o(n log n)": 3,
    "o(n^2)": 4,
    "o(n²)": 4,
    "o(n^3)": 5,
    "o(n³)": 5,
    "o(2^n)": 6,
    "o(2ⁿ)": 6,
    "o(n!)": 7,
}


def complexity_rank(value: str | None) -> int | None:
    """Return a comparable rank for a Big-O string, or None if unknown.

    Lower is cheaper. Unknown or unparseable labels return ``None`` so callers
    never invent an ordering they cannot justify.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    for label, rank in _COMPLEXITY_RANK.items():
        if label in text:
            return rank
    return None


@dataclass
class CodeSignals:
    """Structural facts observed directly in a block of source code."""

    has_code: bool = False
    line_count: int = 0
    loop_count: int = 0
    max_loop_depth: int = 0
    has_nested_loops: bool = False
    uses_hash_map: bool = False
    uses_set: bool = False
    uses_sort: bool = False
    uses_recursion: bool = False
    uses_binary_search: bool = False
    uses_two_pointers: bool = False
    uses_stack: bool = False
    uses_queue: bool = False
    uses_heap: bool = False
    uses_memoization: bool = False
    data_structures: list[str] = field(default_factory=list)
    estimated_time_complexity: str = "Unknown"
    estimated_space_complexity: str = "Unknown"
    basis: str = ""


_RECURSION_SKIP = {
    "if", "for", "while", "return", "print", "range", "len", "str", "int",
    "list", "set", "dict", "sorted", "min", "max", "sum", "abs", "enumerate",
    "zip", "map", "filter", "append", "pop", "push", "dfs", "bfs", "helper",
    "solve",
}


def _estimate_loop_depth(code: str) -> tuple[int, int]:
    """Estimate loop count and maximum nesting depth from indentation.

    Only indentation-based nesting is measurable robustly across the languages
    CodeMemory stores.  The estimate is intentionally coarse and is always
    reported as an estimate, never as a measured fact.
    """
    lines = [ln for ln in code.splitlines() if ln.strip()]
    loop_count = 0
    depth = 0
    max_depth = 0
    indent_stack: list[int] = []

    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        while indent_stack and indent <= indent_stack[-1]:
            indent_stack.pop()
            depth = max(0, depth - 1)
        if re.match(r"^(for|while)\b", stripped):
            loop_count += 1
            depth = len(indent_stack) + 1
            max_depth = max(max_depth, depth)
            indent_stack.append(indent)
        elif re.search(r"\bfor\b|\bwhile\b", stripped):
            # Loop keyword appears inline (comprehension / single line).
            loop_count += 1
    return loop_count, max_depth


def scan_code(code: str | None) -> CodeSignals:
    """Extract conservative structural signals from source code."""
    if not code or not code.strip():
        return CodeSignals(has_code=False, basis="No source code recorded.")

    lowered = code.lower()
    signals = CodeSignals(has_code=True, line_count=len(code.splitlines()))

    signals.loop_count, signals.max_loop_depth = _estimate_loop_depth(code)
    signals.has_nested_loops = signals.max_loop_depth >= 2

    signals.uses_hash_map = any(
        tok in lowered
        for tok in ("hashmap", "unordered_map", "dict(", "{}", "defaultdict", "counter(", "map<")
    )
    signals.uses_set = any(
        tok in lowered for tok in ("set(", "hashset", "unordered_set", "set<", ".add(")
    )
    signals.uses_sort = "sort" in lowered
    signals.uses_binary_search = (
        any(tok in lowered for tok in ("binary search", "bisect", "mid =", "mid=", "low +", "high -"))
        and "while" in lowered
    )
    signals.uses_two_pointers = bool(
        re.search(r"\b(left|low|slow)\b", lowered) and re.search(r"\b(right|high|fast)\b", lowered)
    )
    signals.uses_stack = any(tok in lowered for tok in ("stack", ".pop()", "appendleft", "push("))
    signals.uses_queue = any(tok in lowered for tok in ("queue", "deque", "collections.deque", "appendleft"))
    signals.uses_heap = any(tok in lowered for tok in ("heapq", "heappush", "heappop", "priorityqueue", "priority_queue"))
    signals.uses_memoization = any(
        tok in lowered for tok in ("memo", "lru_cache", "cache[", "@cache", "functools.cache", "dp[", "dp =")
    )

    # Recursion: a def whose name reappears inside the source.
    def_names = set(re.findall(r"def\s+([a-z_][a-z0-9_]*)\s*\(", lowered))
    for name in def_names:
        if name in _RECURSION_SKIP:
            continue
        if len(re.findall(rf"\b{re.escape(name)}\s*\(", lowered)) > 1:
            signals.uses_recursion = True
            break

    ds: list[str] = []
    if signals.uses_hash_map:
        ds.append("HashMap / Dictionary")
    if signals.uses_set:
        ds.append("Set")
    if signals.uses_stack:
        ds.append("Stack")
    if signals.uses_queue:
        ds.append("Queue / Deque")
    if signals.uses_heap:
        ds.append("Heap")
    signals.data_structures = ds

    # Conservative complexity estimate with an explicit basis.
    if signals.max_loop_depth >= 2:
        signals.estimated_time_complexity = "O(n²)" if signals.max_loop_depth == 2 else "O(n³)"
        signals.basis = f"{signals.max_loop_depth} nested loop levels detected (estimated)."
    elif signals.uses_binary_search:
        signals.estimated_time_complexity = "O(log n)"
        signals.basis = "Halving loop pattern detected (estimated)."
    elif signals.uses_sort:
        signals.estimated_time_complexity = "O(n log n)"
        signals.basis = "Sorting call detected (estimated)."
    elif signals.uses_recursion:
        signals.estimated_time_complexity = "Unknown"
        signals.basis = "Recursion detected; complexity depends on branching, not derivable from structure alone."
    elif signals.loop_count >= 1:
        signals.estimated_time_complexity = "O(n)"
        signals.basis = "A single loop level detected (estimated)."
    else:
        signals.estimated_time_complexity = "O(1)"
        signals.basis = "No loops or recursion detected (estimated)."

    if signals.uses_hash_map or signals.uses_memoization or signals.uses_set:
        signals.estimated_space_complexity = "O(n)"
    elif signals.uses_recursion:
        signals.estimated_space_complexity = "O(n) (recursion stack, estimated)"
    else:
        signals.estimated_space_complexity = "O(1)"

    return signals