"""Curated DSA concept taxonomy used for conceptual similarity scoring.

LeetCode topic tags alone are too coarse to answer "what is this problem
conceptually close to?".  A problem tagged ``Array`` is not automatically
related to another ``Array`` problem, while a problem tagged ``Hash Table``
may be a direct reinforcement of a two-pointer problem.  This module encodes
the *conceptual* layer that sits between raw tags and recommendation quality.

Everything here is static, human-curated domain knowledge about DSA *patterns*
-- never a list of problems.  No problem titles, slugs, or URLs live in this
module, so the taxonomy can never fabricate a recommendation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Pattern catalogue
# ---------------------------------------------------------------------------

PATTERN_LABELS: dict[str, str] = {
    "array_traversal": "array traversal",
    "hash_lookup": "hash-map lookup",
    "frequency_counting": "frequency counting",
    "prefix_sum": "prefix sums",
    "sorting": "sorting and ordering",
    "two_pointers": "two pointers",
    "sliding_window": "sliding window",
    "binary_search": "binary search",
    "divide_conquer": "divide and conquer",
    "stack": "stack processing",
    "monotonic_stack": "monotonic stack",
    "queue": "queue processing",
    "linked_list": "linked-list manipulation",
    "fast_slow_pointers": "fast/slow pointers",
    "merge_intervals": "interval merging",
    "tree_traversal": "tree traversal",
    "bst": "binary search tree invariants",
    "recursion": "recursion",
    "dfs": "depth-first search",
    "bfs": "breadth-first search",
    "graph_traversal": "graph traversal",
    "topological_sort": "topological ordering",
    "union_find": "union-find",
    "dp": "dynamic programming",
    "memoization": "memoization",
    "greedy": "greedy selection",
    "heap": "heaps and priority queues",
    "backtracking": "backtracking",
    "trie": "trie / prefix tree",
    "matrix_traversal": "matrix traversal",
    "bit_manipulation": "bit manipulation",
    "math_reasoning": "mathematical reasoning",
    "design": "data-structure design",
    "simulation": "simulation",
    "string_processing": "string processing",
    "counting": "counting",
    "segment_tree": "segment trees",
    "iterator_design": "iterator design",
}


# ---------------------------------------------------------------------------
# Topic tags -> conceptual patterns
# ---------------------------------------------------------------------------

TOPIC_TO_PATTERNS: dict[str, tuple[str, ...]] = {
    "Array": ("array_traversal",),
    "Hash Table": ("hash_lookup", "frequency_counting"),
    "Two Pointers": ("two_pointers",),
    "Binary Search": ("binary_search",),
    "Sliding Window": ("sliding_window", "two_pointers"),
    "String": ("string_processing",),
    "Sorting": ("sorting",),
    "Stack": ("stack",),
    "Monotonic Stack": ("monotonic_stack", "stack"),
    "Queue": ("queue",),
    "Linked List": ("linked_list", "fast_slow_pointers"),
    "Tree": ("tree_traversal", "recursion"),
    "Binary Tree": ("tree_traversal", "recursion"),
    "Binary Search Tree": ("bst", "tree_traversal"),
    "Depth-First Search": ("dfs", "recursion"),
    "Breadth-First Search": ("bfs", "queue"),
    "Graph": ("graph_traversal",),
    "Matrix": ("matrix_traversal",),
    "Dynamic Programming": ("dp",),
    "Memoization": ("memoization", "dp"),
    "Greedy": ("greedy",),
    "Heap (Priority Queue)": ("heap",),
    "Backtracking": ("backtracking", "recursion"),
    "Recursion": ("recursion",),
    "Trie": ("trie", "tree_traversal"),
    "Union Find": ("union_find", "graph_traversal"),
    "Topological Sort": ("topological_sort", "graph_traversal"),
    "Math": ("math_reasoning",),
    "Bit Manipulation": ("bit_manipulation",),
    "Design": ("design",),
    "Divide and Conquer": ("divide_conquer", "recursion"),
    "Segment Tree": ("segment_tree", "tree_traversal"),
    "Binary Indexed Tree": ("segment_tree",),
    "Ordered Set": ("sorting", "design"),
    "Prefix Sum": ("prefix_sum", "array_traversal"),
    "Counting": ("counting", "frequency_counting"),
    "Simulation": ("simulation",),
    "Merge Sort": ("sorting", "divide_conquer"),
    "Quickselect": ("sorting", "divide_conquer"),
    "Data Stream": ("heap", "design"),
    "Iterator": ("iterator_design", "design"),
    "Rolling Hash": ("string_processing", "hash_lookup"),
    "Hash Function": ("hash_lookup", "design"),
    "Game Theory": ("math_reasoning", "dp"),
    "Number Theory": ("math_reasoning",),
    "Combinatorics": ("math_reasoning", "backtracking"),
    "Geometry": ("math_reasoning",),
    "Interactive": ("binary_search",),
}


# ---------------------------------------------------------------------------
# Prerequisite and progression relationships between patterns
# ---------------------------------------------------------------------------

# pattern -> patterns that are useful prerequisites.  Used to identify
# foundational gaps rather than to label the user as "weak".
PATTERN_PREREQUISITES: dict[str, tuple[str, ...]] = {
    "hash_lookup": ("array_traversal",),
    "frequency_counting": ("hash_lookup", "array_traversal"),
    "prefix_sum": ("array_traversal",),
    "two_pointers": ("array_traversal", "sorting"),
    "sliding_window": ("two_pointers",),
    "binary_search": ("sorting",),
    "divide_conquer": ("recursion", "binary_search"),
    "monotonic_stack": ("stack",),
    "fast_slow_pointers": ("linked_list",),
    "tree_traversal": ("recursion",),
    "bst": ("tree_traversal", "binary_search"),
    "dfs": ("recursion", "tree_traversal"),
    "bfs": ("queue", "tree_traversal"),
    "graph_traversal": ("dfs", "bfs"),
    "topological_sort": ("graph_traversal",),
    "union_find": ("graph_traversal",),
    "memoization": ("recursion",),
    "dp": ("recursion", "memoization"),
    "backtracking": ("recursion",),
    "trie": ("tree_traversal",),
    "heap": ("sorting", "tree_traversal"),
    "greedy": ("sorting",),
    "segment_tree": ("tree_traversal", "divide_conquer"),
    "matrix_traversal": ("array_traversal",),
}

# pattern -> adjacent patterns that represent a natural next step.  Adjacency
# is symmetric for scoring purposes; only the forward direction is authored.
PATTERN_ADJACENT: dict[str, tuple[str, ...]] = {
    "array_traversal": ("two_pointers", "prefix_sum", "hash_lookup"),
    "hash_lookup": ("frequency_counting", "prefix_sum", "two_pointers"),
    "frequency_counting": ("hash_lookup", "heap", "counting"),
    "prefix_sum": ("hash_lookup", "sliding_window"),
    "sorting": ("two_pointers", "binary_search", "greedy"),
    "two_pointers": ("sliding_window", "binary_search", "merge_intervals"),
    "sliding_window": ("two_pointers", "prefix_sum"),
    "binary_search": ("divide_conquer", "bst"),
    "divide_conquer": ("binary_search", "segment_tree"),
    "stack": ("monotonic_stack", "backtracking"),
    "monotonic_stack": ("stack", "heap"),
    "queue": ("bfs", "heap"),
    "linked_list": ("fast_slow_pointers", "stack"),
    "fast_slow_pointers": ("linked_list",),
    "tree_traversal": ("dfs", "bfs", "bst"),
    "bst": ("tree_traversal", "binary_search"),
    "recursion": ("dfs", "backtracking", "memoization", "divide_conquer"),
    "dfs": ("graph_traversal", "backtracking", "tree_traversal"),
    "bfs": ("graph_traversal", "queue", "tree_traversal"),
    "graph_traversal": ("topological_sort", "union_find", "dfs", "bfs"),
    "topological_sort": ("graph_traversal", "dp"),
    "union_find": ("graph_traversal",),
    "memoization": ("dp", "recursion"),
    "dp": ("greedy", "memoization"),
    "greedy": ("dp", "heap", "sorting"),
    "heap": ("greedy", "sorting"),
    "backtracking": ("dfs", "recursion"),
    "trie": ("tree_traversal", "string_processing"),
    "matrix_traversal": ("graph_traversal", "dfs", "bfs"),
    "bit_manipulation": ("math_reasoning",),
    "math_reasoning": ("bit_manipulation", "dp"),
    "string_processing": ("hash_lookup", "trie"),
    "counting": ("frequency_counting", "sorting"),
    "design": ("heap", "trie", "iterator_design"),
    "segment_tree": ("divide_conquer", "tree_traversal"),
    "iterator_design": ("design", "stack"),
    "simulation": ("array_traversal", "matrix_traversal"),
}

# Foundational patterns a learner is expected to touch early.  Absence of
# practice is reported as "unpracticed", never as a weakness.
FOUNDATIONAL_PATTERNS: tuple[str, ...] = (
    "array_traversal",
    "hash_lookup",
    "two_pointers",
    "sorting",
    "binary_search",
    "stack",
    "recursion",
    "tree_traversal",
    "bfs",
    "dfs",
    "graph_traversal",
    "dp",
)


# ---------------------------------------------------------------------------
# Data structures and higher-level concept groups
# ---------------------------------------------------------------------------

# pattern -> the concrete data structure(s) it exercises.  Used for the
# "shared data structure" component of conceptual similarity.
PATTERN_DATA_STRUCTURES: dict[str, tuple[str, ...]] = {
    "hash_lookup": ("Hash Table",),
    "frequency_counting": ("Hash Table",),
    "prefix_sum": ("Array",),
    "sorting": ("Array",),
    "two_pointers": ("Array",),
    "sliding_window": ("Array",),
    "binary_search": ("Array",),
    "stack": ("Stack",),
    "monotonic_stack": ("Stack",),
    "queue": ("Queue",),
    "bfs": ("Queue",),
    "linked_list": ("Linked List",),
    "fast_slow_pointers": ("Linked List",),
    "tree_traversal": ("Binary Tree",),
    "bst": ("Binary Search Tree",),
    "dfs": ("Binary Tree",),
    "graph_traversal": ("Graph",),
    "topological_sort": ("Graph",),
    "union_find": ("Union Find",),
    "trie": ("Trie",),
    "heap": ("Heap (Priority Queue)",),
    "segment_tree": ("Segment Tree",),
    "matrix_traversal": ("Matrix",),
    "iterator_design": ("Design",),
}

# Coarse conceptual families.  Two problems that share a family are related
# even when their exact pattern ids differ.
CONCEPT_GROUPS: dict[str, tuple[str, ...]] = {
    "search_and_optimization": (
        "hash_lookup",
        "binary_search",
        "two_pointers",
        "sliding_window",
        "prefix_sum",
        "sorting",
    ),
    "recursive_traversal": (
        "recursion",
        "dfs",
        "bfs",
        "tree_traversal",
        "graph_traversal",
        "backtracking",
        "divide_conquer",
        "memoization",
    ),
    "state_and_decision": (
        "dp",
        "memoization",
        "greedy",
        "backtracking",
        "bit_manipulation",
        "math_reasoning",
    ),
    "linear_structures": (
        "array_traversal",
        "stack",
        "monotonic_stack",
        "queue",
        "linked_list",
        "fast_slow_pointers",
        "matrix_traversal",
        "string_processing",
        "simulation",
    ),
    "ordering_and_selection": (
        "sorting",
        "heap",
        "counting",
        "greedy",
    ),
    "indexed_structures": (
        "trie",
        "segment_tree",
        "bst",
        "union_find",
        "design",
        "iterator_design",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_topic(topic: str) -> str:
    """Normalise a topic tag for lookup (trim only; tags are case-sensitive)."""
    return (topic or "").strip()


def patterns_for_topics(topics: list[str]) -> tuple[str, ...]:
    """Return the ordered, de-duplicated conceptual patterns for topic tags."""
    seen: list[str] = []
    for topic in topics or []:
        for pattern in TOPIC_TO_PATTERNS.get(normalize_topic(topic), ()):  # type: ignore[arg-type]
            if pattern not in seen:
                seen.append(pattern)
    return tuple(seen)


def skill_label(pattern: str) -> str:
    """Human-readable skill label for a pattern id."""
    return PATTERN_LABELS.get(pattern, pattern.replace("_", " "))


def prerequisites_of(pattern: str) -> tuple[str, ...]:
    """Return the prerequisite patterns for a pattern, if any."""
    return PATTERN_PREREQUISITES.get(pattern, ())


def adjacent_of(pattern: str) -> tuple[str, ...]:
    """Return patterns adjacent to ``pattern`` (forward or reverse authored)."""
    forward = PATTERN_ADJACENT.get(pattern, ())
    reverse = tuple(p for p, adj in PATTERN_ADJACENT.items() if pattern in adj)
    merged: list[str] = []
    for item in forward + reverse:
        if item not in merged and item != pattern:
            merged.append(item)
    return tuple(merged)


def is_foundational(pattern: str) -> bool:
    """Return True when the pattern is part of the foundational set."""
    return pattern in FOUNDATIONAL_PATTERNS


def topics_for_pattern(pattern: str) -> tuple[str, ...]:
    """Return the topic tags that map to a given conceptual pattern."""
    return tuple(
        topic
        for topic, patterns in TOPIC_TO_PATTERNS.items()
        if pattern in patterns
    )


def data_structures_of(patterns: Iterable[str]) -> tuple[str, ...]:
    """Return the ordered, de-duplicated data structures for patterns."""
    seen: list[str] = []
    for pattern in patterns:
        for structure in PATTERN_DATA_STRUCTURES.get(pattern, ()):
            if structure not in seen:
                seen.append(structure)
    return tuple(seen)


def concept_groups_of(patterns: Iterable[str]) -> tuple[str, ...]:
    """Return the concept families that a set of patterns belongs to."""
    pattern_set = set(patterns)
    return tuple(
        group for group, members in CONCEPT_GROUPS.items() if pattern_set & set(members)
    )


def describe_patterns(patterns: list[str] | tuple[str, ...]) -> str:
    """Render a comma-separated human-readable description of patterns."""
    labels = [skill_label(p) for p in patterns]
    return ", ".join(labels)
