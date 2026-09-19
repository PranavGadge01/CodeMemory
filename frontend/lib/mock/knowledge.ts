import type { GraphEdge, GraphNode, KnowledgeCluster, KnowledgeGraph } from "@/lib/types";
import { getMockProblems, problemIdFor } from "@/lib/mock/problems";
import { isSolved, latestAnalysis, submissionsOf } from "@/lib/mock/derive";

const CONCEPTS: Record<string, string> = {
  "Dynamic Programming": "Overlapping Subproblems",
  Backtracking: "Decision Tree Search",
  "Two Pointers": "Invariant Narrowing",
  "Binary Search": "Monotone Search Space",
  "Sliding Window": "Amortised Bounded State",
  "Depth-First Search": "Recursive Exhaustion",
  "Breadth-First Search": "Level-Order Expansion",
  "Hash Table": "Constant-Time Lookup",
  Heap: "Partial Ordering",
  Trie: "Prefix Sharing",
  Graph: "Adjacency Structure",
  Matrix: "Grid Coordinate Space",
  Greedy: "Local Optimum Choice",
  Stack: "LIFO Ordering",
  "Linked List": "Pointer Rewiring",
  Sorting: "Ordering As A Precondition",
  String: "Character-Level State",
  Array: "Indexed Contiguity",
  Math: "Numeric Invariants",
  Recursion: "Self-Similar Subproblem",
  "Union Find": "Disjoint Set Merging",
  "Topological Sort": "Dependency Ordering",
  "Monotonic Stack": "Next-Greater Element",
  "Divide and Conquer": "Split, Solve, Merge",
  "Bit Manipulation": "Boolean Algebra",
  "String Matching": "Pattern Alignment",
  Tree: "Hierarchical Traversal",
  "Binary Tree": "Ordered Hierarchy",
  Design: "State Encapsulation",
  Counting: "Frequency Buckets",
  "Merge Sort": "Stable Partition",
  "Fast & Slow Pointers": "Cycle Detection",
  "Bracket Sequences": "Well-Formedness",
  Simulation: "Stepwise Reproduction",
  "Newton's Method": "Iterative Refinement",
  "Z Algorithm": "Linear Pattern Matching",
};

function topicId(topic: string): string {
  return `topic_${topic.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
}
function conceptId(topic: string): string {
  return `concept_${topic.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
}
function languageId(language: string): string {
  return `lang_${language.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
}
function approachId(approach: string): string {
  return `appr_${approach.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
}
function mistakeId(mistake: string): string {
  return `mistake_${mistake.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 40)}`;
}

/**
 * Builds the graph the same way the backend `KnowledgeGraphBuilder` does:
 * Problem nodes link to Topic, Language, Approach and Mistake nodes.
 * Concept nodes are CodeMemory's own layer — the idea that a topic is a
 * surface for a transferable technique.
 */
export function getMockKnowledgeGraph(): KnowledgeGraph {
  const problems = getMockProblems();
  const nodes = new Map<string, GraphNode>();
  const edges = new Set<string>();
  const edgeList: GraphEdge[] = [];

  const addNode = (node: GraphNode): void => {
    nodes.set(node.id, node);
  };
  const addEdge = (edge: GraphEdge): void => {
    const key = `${edge.sourceId}→${edge.targetId}:${edge.relationship}`;
    if (edges.has(key)) return;
    edges.add(key);
    edgeList.push(edge);
  };

  for (const problem of problems) {
    addNode({ id: problem.id, label: problem.title, type: "Problem" });

    for (const topic of problem.topics) {
      addNode({ id: topicId(topic), label: topic, type: "Topic" });
      addEdge({ sourceId: problem.id, targetId: topicId(topic), relationship: "TAGGED_WITH" });

      const concept = CONCEPTS[topic];
      if (concept) {
        addNode({ id: conceptId(topic), label: concept, type: "Concept" });
        addEdge({
          sourceId: topicId(topic),
          targetId: conceptId(topic),
          relationship: "REQUIRES_CONCEPT",
        });
      }
    }

    for (const sub of submissionsOf(problem)) {
      addNode({ id: languageId(sub.language), label: sub.language, type: "Language" });
      addEdge({ sourceId: problem.id, targetId: languageId(sub.language), relationship: "SOLVED_IN" });
    }

    for (const attempt of problem.attempts) {
      const analysis = attempt.analysis ?? latestAnalysis(problem);
      if (!analysis) continue;
      const label = analysis.approachName;
      addNode({ id: approachId(label), label, type: "Approach" });
      addEdge({
        sourceId: problem.id,
        targetId: approachId(label),
        relationship: "USES_APPROACH",
      });
      for (const mistake of attempt.mistakes) {
        addNode({ id: mistakeId(mistake), label: mistake, type: "Mistake" });
        addEdge({
          sourceId: approachId(label),
          targetId: mistakeId(mistake),
          relationship: "ENCOUNTERED_MISTAKE",
        });
      }
    }
  }

  return { nodes: [...nodes.values()], edges: edgeList };
}

export function getMockClusters(): KnowledgeCluster[] {
  const problems = getMockProblems();
  const byTopic = new Map<string, typeof problems>();

  for (const problem of problems) {
    const primary = problem.topics[0] ?? "Uncategorised";
    if (!byTopic.has(primary)) byTopic.set(primary, []);
    byTopic.get(primary)!.push(problem);
  }

  return [...byTopic.entries()]
    .filter(([, group]) => group.length >= 2)
    .map(([topic, group]) => {
      const solved = group.filter(isSolved).length;
      return {
        id: topicId(topic),
        title: topic,
        description: `${group.length} problems · ${solved} solved`,
        topicId: topicId(topic),
        problemIds: group.map((problem) => problem.id),
        masteryPct: Math.round((solved / group.length) * 100),
      };
    })
    .sort((a, b) => b.problemIds.length - a.problemIds.length);
}

export { topicId, conceptId, problemIdFor };
