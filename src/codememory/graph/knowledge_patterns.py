"""Knowledge patterns extraction from the knowledge graph.

Derives reusable pattern summaries and their relationships from
the user's actual problem-solving history.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from codememory.graph.knowledge_graph import KnowledgeGraph, GraphNode, GraphEdge
from codememory.learning.taxonomy import (
    patterns_for_topics,
    PATTERN_LABELS,
)


class KnowledgePatternExtractor:
    """Extracts pattern summaries and relationships from a knowledge graph."""

    # Map edge types that connect problems to approaches
    APPROACH_NODE_TYPE = "Approach"
    PROBLEM_NODE_TYPE = "Problem"
    TOPIC_NODE_TYPE = "Topic"

    def extract_patterns(
        self,
        graph: KnowledgeGraph,
        problems_data: Dict[str, dict]  # problem_id -> {topics, approaches, languages, attempts}
    ) -> Tuple[List[dict], List[dict]]:
        """
        Extract pattern summaries and their relationships from the knowledge graph.

        Returns:
            Tuple of (patterns, relationships) where:
            - patterns: List of pattern summary dicts
            - relationships: List of relationship dicts between patterns
        """
        # Extract patterns from topics -> conceptual patterns
        pattern_data = self._extract_pattern_data(graph, problems_data)

        # Build relationships between patterns
        relationships = self._build_pattern_relationships(
            pattern_data, graph
        )

        return list(pattern_data.values()), relationships

    def _extract_pattern_data(
        self,
        graph: KnowledgeGraph,
        problems_data: Dict[str, dict]
    ) -> Dict[str, dict]:
        """Extract pattern summaries from the graph and problem data."""
        patterns: Dict[str, dict] = {}

        # Map patterns to their counts
        pattern_problem_counts: Dict[str, Set[str]] = defaultdict(set)
        pattern_accepts: Dict[str, int] = defaultdict(int)

        # Process approach nodes directly from the graph
        approach_nodes: List[GraphNode] = []
        for node in graph.nodes:
            if node.type == "Topic":
                # Topics map to patterns
                topic_patterns = patterns_for_topics([node.label])
                for pattern_id in topic_patterns:
                    approach_nodes.append(node)  # Add as representative

        # Process problems and their approaches
        for problem in graph.nodes:
            if problem.type != "Problem":
                continue

            # Get problem data if available
            problem_id = problem.id
            if problem_id.startswith("prob_"):
                problem_id = problem_id[5:]

            problem_data = problems_data.get(problem_id, {})
            topics = problem_data.get("topics", [])
            approaches = problem_data.get("approaches", [])

            # Track patterns from topics
            for topic in topics:
                topic_patterns = patterns_for_topics([topic])
                for pattern_id in topic_patterns:
                    pattern_problem_counts[pattern_id].add(problem_id)

            # Track first-attempt accepts for each pattern
            attempts = problem_data.get("attempts", [])
            is_solved = problem_data.get("is_solved", False)

            # Count first-attempt accepts
            if attempts and attempts[0].get("status") == "Accepted":
                for topic in topics:
                    for pattern_id in patterns_for_topics([topic]):
                        pattern_accepts[pattern_id] += 1

            # Track patterns from approaches
            for approach in approaches:
                approach_lower = approach.lower().strip()
                # Try to match approach to known patterns
                matched_patterns = self._match_approach_to_patterns(approach_lower)
                for pattern_id in matched_patterns:
                    pattern_problem_counts[pattern_id].add(problem_id)

        # Build pattern summaries
        for pattern_id, problems in pattern_problem_counts.items():
            count = len(problems)
            if count >= 1:  # Only include patterns with at least 1 problem
                label = PATTERN_LABELS.get(pattern_id, pattern_id.replace("_", " ").title())
                description = self._get_pattern_description(pattern_id)

                patterns[pattern_id] = {
                    "id": pattern_id,
                    "label": label,
                    "description": description,
                    "problemCount": count,
                    "firstAttemptAccepts": pattern_accepts.get(pattern_id, 0)
                }

        return patterns

    def _match_approach_to_patterns(self, approach: str) -> List[str]:
        """Try to match an approach string to known patterns."""
        matches = []
        approach_lower = approach.lower()

        for pattern_id, label in PATTERN_LABELS.items():
            if label.lower() in approach_lower or approach_lower in label.lower():
                matches.append(pattern_id)

        # If no direct match, check for common keywords
        if not matches:
            keywords_to_pattern = {
                "sliding": "sliding_window",
                "two pointer": "two_pointers",
                "hash map": "hash_lookup",
                "prefix": "prefix_sum",
                "binary search": "binary_search",
                "stack": "stack",
                "queue": "queue",
                "dfs": "depth-first search",
                "bfs": "breadth-first search",
                "recursive": "recursion",
                "dp": "dynamic programming",
                "greedy": "greedy",
                "backtrack": "backtracking",
                "trie": "trie",
                "heap": "heaps and priority queues",
            }
            for keyword, pattern_id in keywords_to_pattern.items():
                if keyword in approach_lower:
                    matches.append(pattern_id)

        # Deduplicate while preserving order
        seen = set()
        unique_matches = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique_matches.append(m)

        return unique_matches

    def _get_pattern_description(self, pattern_id: str) -> str:
        """Get a brief description for a pattern."""
        descriptions = {
            "sliding_window": "A technique that uses two pointers to maintain a window of elements satisfying a condition, useful for substring/subarray problems.",
            "hash_lookup": "Using a hash table for O(1) lookups, commonly for counting, grouping, or finding complements.",
            "prefix_sum": "Precomputing cumulative sums to answer range sum queries efficiently.",
            "two_pointers": "Using two pointers moving from opposite ends or same direction, efficient for sorted arrays.",
            "binary_search": "Doubling search space by repeatedly dividing, used for finding boundaries or searching sorted data.",
            "stack": "LIFO data structure for tracking state, useful for undo operations, parentheses matching, and next-greatest elements.",
            "queue": "FIFO data structure, often for BFS or sliding window maximum/minimum.",
            "recursion": "Solving by reducing to smaller subproblems, often with depth-first traversal.",
            "depth-first search": "Traversing graph/tree by exploring as far as possible along each branch before backtracking.",
            "breadth-first search": "Traversing by exploring all neighbors at the present depth before moving to the next level.",
            "graph_traversal": "Visiting every node in a graph exactly once, either depth-first or breadth-first.",
            "union_find": "Data structure tracking disjoint sets, useful for connectivity queries.",
            "topological_sort": "Ordering nodes in a DAG such that all edges point forward, used for dependency resolution.",
            "dynamic_programming": "Storing subproblem results to avoid recomputation, transforming exponential to polynomial time.",
            "memoization": "Caching function results, a top-down approach to dynamic programming.",
            "greedy": "Making locally optimal choices at each step, proven correct for certain problem structures.",
            "backtracking": "Building candidates incrementally and abandoning a candidate as soon as it's determined invalid.",
            "trie": "Tree structure for prefix-based string operations and efficient word lookup.",
            "divide_conquer": "Breaking problem into subproblems, solving recursively, and combining solutions.",
            "heap": "Binary heap for efficient min/max extraction, used in Dijkstra, merge k sorted lists, etc.",
            "merge_intervals": "Combining overlapping intervals, useful for scheduling and coverage problems.",
            "matrix_traversal": "Systematic navigation of grid cells, often with DFS/BFS for connected components.",
            "string_processing": "Manipulating and analyzing text data, including pattern matching and transformation.",
            "frequency_counting": "Using hash maps to count occurrences, common in anagram and validation problems.",
            "sorting_and_ordering": "Arranging elements in order to enable efficient search, grouping, and optimization.",
            "monotonic_stack": "Stack maintaining monotonic property for efficient range queries.",
            "linked_list": "Sequential data structure where elements point to the next, useful for O(1) insert/delete.",
            "fast_slow_pointers": "Two pointers moving at different speeds to find cycles or middle elements.",
            "binary_search_tree": "Ordered tree enabling O(log n) search, insertion, and deletion.",
            "bit_manipulation": "Using bitwise operations for efficient computation and state encoding.",
            "mathematical_reasoning": "Applying mathematical theorems and properties to derive solutions.",
            "design": "Implementing data structures or algorithms from specifications, often with complexity constraints.",
            "simulation": "Step-by-step modeling of a process, often with careful state tracking.",
            "counting": "Combinatorial counting using permutations, combinations, or inclusion-exclusion.",
            "segment_tree": "Tree structure for efficient range queries on arrays, including sums, minimums, maximums.",
            "iterator_design": "Implementing custom iterators for lazy evaluation and memory efficiency.",
        }
        return descriptions.get(pattern_id, f"A technique for solving problems involving {pattern_id.replace('_', ' ')}.")

    def _build_pattern_relationships(
        self,
        patterns: Dict[str, dict],
        graph: KnowledgeGraph
    ) -> List[dict]:
        """Build relationships between patterns based on shared problems."""
        relationships = []

        # Build problem -> patterns mapping
        problem_patterns: Dict[str, Set[str]] = defaultdict(set)

        for node in graph.nodes:
            if node.type == "Topic":
                topic_patterns = patterns_for_topics([node.label])
                problem_id = node.id
                for pattern_id in topic_patterns:
                    problem_patterns[problem_id].add(pattern_id)

        # Find pairs of patterns with shared problems
        pattern_pairs: Dict[Tuple[str, str], int] = defaultdict(int)

        for problem_id, pattern_set in problem_patterns.items():
            pattern_list = list(pattern_set)
            for i, p1 in enumerate(pattern_list):
                for p2 in pattern_list[i + 1:]:
                    # Sort to ensure consistent ordering
                    pair = tuple(sorted([p1, p2]))
                    pattern_pairs[pair] += 1

        # Filter to pairs with 2+ shared problems
        for (p1, p2), count in pattern_pairs.items():
            if count >= 2:  # At least 2 shared problems
                label1 = patterns.get(p1, {}).get("label", p1)
                label2 = patterns.get(p2, {}).get("label", p2)
                relationships.append({
                    "patternA": label1,
                    "patternB": label2,
                    "sharedProblemCount": count
                })

        # Sort by shared count descending
        relationships.sort(key=lambda r: (-r["sharedProblemCount"], r["patternA"], r["patternB"]))

        # Limit to top 5 relationships
        return relationships[:5]
