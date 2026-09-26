import type {
  Attempt,
  Difficulty,
  Language,
  Platform,
  Problem,
  ProblemNote,
  SolutionAnalysis,
  Submission,
  SubmissionStatus,
} from "@/lib/types";
import { daysAgo } from "@/lib/mock/clock";
import {
  around,
  chance,
  createRng,
  floatIn,
  intIn,
  pick,
  pickMany,
  type Rng,
} from "@/lib/mock/random";

/**
 * Seed catalogue.
 *
 * The first 21 entries are the problems actually present in this repository's
 * seeded knowledge base (the `knowledge/<slug>/` folders). The remainder is
 * additional curated history so the tables, queues and charts have realistic
 * density — a real user has far more than 21 solved problems.
 */
interface ProblemSeed {
  slug: string;
  title: string;
  difficulty: Difficulty;
  topics: string[];
  platform?: Platform;
}

export const PROBLEM_SEEDS: ProblemSeed[] = [
  // --- Seeded from the real CodeMemory knowledge base ---
  { slug: "two-sum", title: "Two Sum", difficulty: "Easy", topics: ["Array", "Hash Table"] },
  {
    slug: "add-binary",
    title: "Add Binary",
    difficulty: "Easy",
    topics: ["Math", "String", "Bit Manipulation"],
  },
  {
    slug: "length-of-last-word",
    title: "Length of Last Word",
    difficulty: "Easy",
    topics: ["String"],
  },
  {
    slug: "longest-common-prefix",
    title: "Longest Common Prefix",
    difficulty: "Easy",
    topics: ["Array", "String", "Trie"],
  },
  {
    slug: "merge-sorted-array",
    title: "Merge Sorted Array",
    difficulty: "Easy",
    topics: ["Array", "Two Pointers", "Sorting"],
  },
  { slug: "plus-one", title: "Plus One", difficulty: "Easy", topics: ["Array", "Math"] },
  {
    slug: "roman-to-integer",
    title: "Roman to Integer",
    difficulty: "Easy",
    topics: ["Hash Table", "Math", "String"],
  },
  {
    slug: "search-insert-position",
    title: "Search Insert Position",
    difficulty: "Easy",
    topics: ["Array", "Binary Search"],
  },
  { slug: "sqrtx", title: "Sqrt(x)", difficulty: "Easy", topics: ["Math", "Binary Search"] },
  {
    slug: "maximum-depth-of-binary-tree",
    title: "Maximum Depth of Binary Tree",
    difficulty: "Easy",
    topics: ["Tree", "Depth-First Search", "Binary Tree"],
  },
  {
    slug: "3sum",
    title: "3Sum",
    difficulty: "Medium",
    topics: ["Array", "Two Pointers", "Sorting"],
  },
  {
    slug: "3sum-closest",
    title: "3Sum Closest",
    difficulty: "Medium",
    topics: ["Array", "Two Pointers", "Sorting"],
  },
  {
    slug: "find-first-and-last-position-of-element-in-sorted-array",
    title: "Find First and Last Position of Element in Sorted Array",
    difficulty: "Medium",
    topics: ["Array", "Binary Search"],
  },
  {
    slug: "find-the-index-of-the-first-occurrence-in-a-string",
    title: "Find the Index of the First Occurrence in a String",
    difficulty: "Medium",
    topics: ["Two Pointers", "String", "String Matching"],
  },
  {
    slug: "generate-parentheses",
    title: "Generate Parentheses",
    difficulty: "Medium",
    topics: ["String", "Dynamic Programming", "Backtracking"],
  },
  {
    slug: "integer-to-roman",
    title: "Integer to Roman",
    difficulty: "Medium",
    topics: ["Hash Table", "Math", "String"],
  },
  {
    slug: "letter-combinations-of-a-phone-number",
    title: "Letter Combinations of a Phone Number",
    difficulty: "Medium",
    topics: ["Hash Table", "String", "Backtracking"],
  },
  {
    slug: "remove-nth-node-from-end-of-list",
    title: "Remove Nth Node From End of List",
    difficulty: "Medium",
    topics: ["Linked List", "Two Pointers"],
  },
  {
    slug: "search-in-rotated-sorted-array",
    title: "Search in Rotated Sorted Array",
    difficulty: "Medium",
    topics: ["Array", "Binary Search"],
  },
  {
    slug: "string-to-integer-atoi",
    title: "String to Integer (atoi)",
    difficulty: "Medium",
    topics: ["String"],
  },
  {
    slug: "swap-nodes-in-pairs",
    title: "Swap Nodes in Pairs",
    difficulty: "Medium",
    topics: ["Linked List", "Recursion"],
  },
  {
    slug: "zigzag-conversion",
    title: "Zigzag Conversion",
    difficulty: "Medium",
    topics: ["String"],
  },
  // --- Additional curated history ---
  {
    slug: "longest-substring-without-repeating-characters",
    title: "Longest Substring Without Repeating Characters",
    difficulty: "Medium",
    topics: ["Hash Table", "String", "Sliding Window"],
  },
  {
    slug: "longest-palindromic-substring",
    title: "Longest Palindromic Substring",
    difficulty: "Medium",
    topics: ["Two Pointers", "String", "Dynamic Programming"],
  },
  {
    slug: "container-with-most-water",
    title: "Container With Most Water",
    difficulty: "Medium",
    topics: ["Array", "Two Pointers", "Greedy"],
  },
  {
    slug: "valid-parentheses",
    title: "Valid Parentheses",
    difficulty: "Easy",
    topics: ["String", "Stack"],
  },
  {
    slug: "merge-two-sorted-lists",
    title: "Merge Two Sorted Lists",
    difficulty: "Easy",
    topics: ["Linked List", "Recursion"],
  },
  {
    slug: "best-time-to-buy-and-sell-stock",
    title: "Best Time to Buy and Sell Stock",
    difficulty: "Medium",
    topics: ["Array", "Dynamic Programming"],
  },
  {
    slug: "group-anagrams",
    title: "Group Anagrams",
    difficulty: "Medium",
    topics: ["Array", "Hash Table", "Sorting", "String"],
  },
  {
    slug: "combination-sum",
    title: "Combination Sum",
    difficulty: "Medium",
    topics: ["Array", "Backtracking"],
  },
  {
    slug: "permutations",
    title: "Permutations",
    difficulty: "Medium",
    topics: ["Array", "Backtracking"],
  },
  {
    slug: "subsets",
    title: "Subsets",
    difficulty: "Medium",
    topics: ["Array", "Backtracking", "Bit Manipulation"],
  },
  {
    slug: "house-robber",
    title: "House Robber",
    difficulty: "Medium",
    topics: ["Array", "Dynamic Programming"],
  },
  {
    slug: "coin-change",
    title: "Coin Change",
    difficulty: "Medium",
    topics: ["Array", "Dynamic Programming", "Breadth-First Search"],
  },
  {
    slug: "number-of-islands",
    title: "Number of Islands",
    difficulty: "Medium",
    topics: ["Array", "Depth-First Search", "Breadth-First Search", "Union Find", "Matrix"],
  },
  {
    slug: "rotting-oranges",
    title: "Rotting Oranges",
    difficulty: "Medium",
    topics: ["Array", "Breadth-First Search", "Matrix"],
  },
  {
    slug: "kth-largest-element-in-an-array",
    title: "Kth Largest Element in an Array",
    difficulty: "Medium",
    topics: ["Array", "Divide and Conquer", "Sorting", "Heap"],
  },
  {
    slug: "top-k-frequent-elements",
    title: "Top K Frequent Elements",
    difficulty: "Medium",
    topics: ["Array", "Hash Table", "Sorting", "Heap", "Counting"],
  },
  {
    slug: "course-schedule",
    title: "Course Schedule",
    difficulty: "Medium",
    topics: ["Depth-First Search", "Breadth-First Search", "Graph", "Topological Sort"],
  },
  {
    slug: "implement-trie-prefix-tree",
    title: "Implement Trie (Prefix Tree)",
    difficulty: "Medium",
    topics: ["Hash Table", "String", "Design", "Trie"],
  },
  {
    slug: "design-add-and-search-words-data-structure",
    title: "Design Add and Search Words Data Structure",
    difficulty: "Medium",
    topics: ["String", "Depth-First Search", "Design", "Trie"],
  },
  {
    slug: "koko-eating-bananas",
    title: "Koko Eating Bananas",
    difficulty: "Medium",
    topics: ["Array", "Binary Search"],
  },
  {
    slug: "median-of-two-sorted-arrays",
    title: "Median of Two Sorted Arrays",
    difficulty: "Hard",
    topics: ["Array", "Binary Search", "Divide and Conquer"],
  },
  {
    slug: "merge-k-sorted-lists",
    title: "Merge k Sorted Lists",
    difficulty: "Hard",
    topics: ["Linked List", "Divide and Conquer", "Heap", "Merge Sort"],
  },
  {
    slug: "trapping-rain-water",
    title: "Trapping Rain Water",
    difficulty: "Hard",
    topics: ["Array", "Two Pointers", "Dynamic Programming", "Stack", "Monotonic Stack"],
  },
  {
    slug: "minimum-window-substring",
    title: "Minimum Window Substring",
    difficulty: "Hard",
    topics: ["Hash Table", "String", "Sliding Window"],
  },
  {
    slug: "edit-distance",
    title: "Edit Distance",
    difficulty: "Hard",
    topics: ["String", "Dynamic Programming"],
  },
  {
    slug: "regular-expression-matching",
    title: "Regular Expression Matching",
    difficulty: "Hard",
    topics: ["String", "Dynamic Programming", "Recursion"],
  },
  {
    slug: "serialize-and-deserialize-binary-tree",
    title: "Serialize and Deserialize Binary Tree",
    difficulty: "Hard",
    topics: ["Tree", "Depth-First Search", "Breadth-First Search", "Design", "Binary Tree"],
  },
  {
    slug: "sliding-window-maximum",
    title: "Sliding Window Maximum",
    difficulty: "Hard",
    topics: ["Array", "Queue", "Sliding Window", "Heap", "Monotonic Queue"],
  },
  {
    slug: "find-median-from-data-stream",
    title: "Find Median from Data Stream",
    difficulty: "Hard",
    topics: ["Heap", "Design", "Two Pointers", "Data Stream"],
  },
  {
    slug: "longest-consecutive-sequence",
    title: "Longest Consecutive Sequence",
    difficulty: "Medium",
    topics: ["Array", "Hash Table", "Union Find"],
  },
  {
    slug: "binary-tree-inorder-traversal",
    title: "Binary Tree Inorder Traversal",
    difficulty: "Easy",
    topics: ["Tree", "Depth-First Search", "Binary Tree", "Stack"],
  },
  {
    slug: "lowest-common-ancestor-of-a-binary-tree",
    title: "Lowest Common Ancestor of a Binary Tree",
    difficulty: "Medium",
    topics: ["Tree", "Depth-First Search", "Binary Tree"],
  },
  {
    slug: "word-break",
    title: "Word Break",
    difficulty: "Medium",
    topics: ["Array", "Hash Table", "String", "Dynamic Programming", "Trie"],
  },
];

const LANGUAGES: Language[] = ["Python 3", "Java", "C++", "JavaScript", "Go", "TypeScript"];

const RUNTIME_BASELINE: Record<Difficulty, { ms: number; spread: number; memory: number }> = {
  Easy: { ms: 38, spread: 24, memory: 16.4 },
  Medium: { ms: 92, spread: 58, memory: 19.8 },
  Hard: { ms: 240, spread: 150, memory: 27.5 },
  Unknown: { ms: 60, spread: 30, memory: 18 },
};

/**
 * Realistic attempt arcs. CodeMemory's core promise is that failed attempts
 * are preserved alongside the accepted one, so most problems carry a
 * visible TLE → WA → Accepted journey.
 */
const EVOLUTION_ARCS: Record<number, SubmissionStatus[][]> = {
  1: [["Accepted"]],
  2: [
    ["Accepted", "Accepted"],
    ["Wrong Answer", "Accepted"],
    ["Time Limit Exceeded", "Accepted"],
    ["Compile Error", "Accepted"],
  ],
  3: [
    ["Time Limit Exceeded", "Wrong Answer", "Accepted"],
    ["Wrong Answer", "Wrong Answer", "Accepted"],
    ["Time Limit Exceeded", "Accepted", "Accepted"],
    ["Runtime Error", "Wrong Answer", "Accepted"],
    ["Accepted", "Time Limit Exceeded", "Accepted"],
  ],
  4: [
    ["Time Limit Exceeded", "Wrong Answer", "Time Limit Exceeded", "Accepted"],
    ["Wrong Answer", "Compile Error", "Time Limit Exceeded", "Accepted"],
    ["Time Limit Exceeded", "Time Limit Exceeded", "Wrong Answer", "Accepted"],
    ["Wrong Answer", "Wrong Answer", "Wrong Answer", "Accepted"],
  ],
};

const UNSOLVED_ARCS: SubmissionStatus[][] = [
  ["Wrong Answer", "Time Limit Exceeded"],
  ["Time Limit Exceeded", "Time Limit Exceeded", "Wrong Answer"],
  ["Wrong Answer", "Wrong Answer"],
];

const APPROACHES = [
  "Brute Force",
  "Hash Map Lookup",
  "Two Pointers",
  "Sliding Window",
  "Binary Search",
  "Depth-First Search",
  "Breadth-First Search",
  "Dynamic Programming",
  "Backtracking",
  "Greedy",
  "Monotonic Stack",
  "Union Find",
  "Topological Sort",
  "Heap / Priority Queue",
  "Bit Manipulation",
  "Fast & Slow Pointers",
];

const MISTAKES = [
  "Off-by-one error on the loop bound",
  "Forgot to handle the empty-input edge case",
  "Used an unsorted array where the two-pointer trick needs a sorted one",
  "Mutated the input while iterating over it",
  "Integer overflow on the running product",
  "Compared object identity instead of value equality",
  "Missed the duplicate-suppression check",
  "Recursion base case written one level too shallow",
  "Used a List where a Set was needed for O(1) lookups",
  "Assumed the input was already sorted",
];

const INSIGHTS: Record<string, string[]> = {
  Hash: [
    "Trade O(n) extra space for O(1) membership checks",
    "Store the complement, not the element, in the map",
  ],
  Pointers: [
    "Sorting first converts the O(n^2) scan into a single linear pass",
    "Move the pointer that is currently worse for the objective",
  ],
  Window: [
    "The window only ever moves right, so the work is amortised O(n)",
    "Shrink from the left until the invariant holds again",
  ],
  Search: [
    "The search space is monotone, so binary search applies",
    "Choose the half that must contain the answer based on the midpoint test",
  ],
  DP: [
    "State = index plus whatever the constraint depends on",
    "The recurrence only needs the previous row, so space drops to O(n)",
  ],
  Default: [
    "Reduce the problem to a known primitive instead of solving it from scratch",
    "The invariant is what makes the greedy choice safe",
  ],
};

function approachFor(rng: Rng, topics: string[], attemptNumber: number): string {
  if (attemptNumber === 1) return chance(rng, 0.72) ? "Brute Force" : pick(rng, APPROACHES);
  const topicMatch = APPROACHES.find((approach) =>
    topics.some((topic) => topic.toLowerCase().includes(approach.toLowerCase())),
  );
  return topicMatch ?? pick(rng, APPROACHES.slice(1));
}

function insightsFor(rng: Rng, topics: string[]): string[] {
  const bucket =
    Object.keys(INSIGHTS).find((key) => topics.some((t) => t.toLowerCase().includes(key.toLowerCase()))) ??
    "Default";
  return pickMany(rng, INSIGHTS[bucket] as string[], 2);
}

function complexityFor(approach: string): { time: string; space: string } {
  if (approach === "Brute Force") return { time: "O(n²)", space: "O(1)" };
  if (approach.includes("Hash")) return { time: "O(n)", space: "O(n)" };
  if (approach.includes("Pointer") || approach.includes("Window")) return { time: "O(n)", space: "O(1)" };
  if (approach.includes("Search")) return { time: "O(log n)", space: "O(1)" };
  if (approach.includes("Heap")) return { time: "O(n log n)", space: "O(n)" };
  if (approach.includes("Tree") || approach.includes("Depth") || approach.includes("Breadth"))
    return { time: "O(V + E)", space: "O(V)" };
  if (approach.includes("Dynamic")) return { time: "O(n·m)", space: "O(n)" };
  return { time: "O(n log n)", space: "O(n)" };
}

function hashId(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-|-$/g, "");
}

function buildAttempts(
  rng: Rng,
  problem: ProblemSeed,
  problemId: string,
  startDay: number,
): Attempt[] {
  const baseline = RUNTIME_BASELINE[problem.difficulty];

  // A small set of problems stay unsolved — keeps the dashboard honest.
  const unsolved = problem.difficulty !== "Easy" && chance(rng, 0.14);
  const attemptCount = unsolved ? pick(rng, [2, 3]) : Math.min(arcCount(rng, problem), 4);
  const arc = unsolved ? pick(rng, UNSOLVED_ARCS) : pick(rng, EVOLUTION_ARCS[attemptCount]);

  // Cursor moves forward in time across attempts.
  let cursor = startDay;

  return arc.map((status, index): Attempt => {
    const attemptNumber = index + 1;
    const approach = approachFor(rng, problem.topics, attemptNumber);
    const language: Language = pickLanguage(rng, problem, attemptNumber);
    const submittedAt = daysAgo(Math.max(0, cursor));
    cursor -= intIn(rng, 0, 4);

    const accepted = status === "Accepted";
    const complexity = complexityFor(approach);

    // Runtime improves as attempts progress — brute force is slow, later
    // approaches beat it. Failures carry no percentile.
    const progression = accepted
      ? around(rng, baseline.ms * (problem.difficulty === "Hard" ? 0.72 : 0.6) * (1 - index * 0.12), baseline.spread)
      : around(rng, baseline.ms * (1.9 + index * 0.35), baseline.spread * 1.4);
    const runtimeMs = Math.max(2, progression);
    const memoryMb = accepted
      ? floatIn(rng, baseline.memory * 0.7, baseline.memory * 1.25, 2)
      : floatIn(rng, baseline.memory * 1.1, baseline.memory * 1.9, 2);
    const beatsPercent = accepted ? intIn(rng, 58, 99) : null;

    const analysis: SolutionAnalysis | null = accepted
      ? {
          approachName: approach,
          timeComplexity: complexity.time,
          spaceComplexity: complexity.space,
          keyInsights: insightsFor(rng, problem.topics),
          tradeOffs:
            approach === "Brute Force"
              ? "Constant space, but quadratic time will not scale past n ≈ 10⁴."
              : "Linear time is bought with linear auxiliary space.",
          bottleneck: approach === "Brute Force" ? "Nested loop dominates the runtime" : null,
        }
      : null;

    const submission: Submission = {
      id: `leetcode_${hashId(`${problemId}:${attemptNumber}:${submittedAt}`)}`,
      problemId,
      attemptId: null,
      code: "",
      language,
      status,
      runtimeMs: Math.round(runtimeMs),
      memoryMb,
      beatsPercent,
      submittedAt,
      errorMessage: null,
      submissionHash: hashId(`${problem.slug}:${language}:${status}:${submittedAt}`),
      sourceProvider: "LeetCode",
      sourceAccount: null,
    };
    submission.attemptId = `attempt_${hashId(problemId + attemptNumber)}`;

    return {
      id: submission.attemptId as string,
      problemId,
      attemptNumber,
      approachSummary: `Attempt ${attemptNumber} — ${approach}`,
      reasoning: accepted
        ? `${approach} generalises the brute-force scan by eliminating the redundant work in the inner loop.`
        : null,
      mistakes: accepted && chance(rng, 0.6) ? pickMany(rng, MISTAKES, intIn(rng, 1, 2)) : [],
      analysis,
      status,
      createdAt: submittedAt,
      updatedAt: submittedAt,
      submissions: [submission],
    };
  });
}

function arcCount(rng: Rng, problem: ProblemSeed): number {
  const roll = rng();
  switch (problem.difficulty) {
    case "Easy":
      return roll < 0.82 ? 1 : 2;
    case "Medium":
      return roll < 0.42 ? 1 : roll < 0.76 ? 2 : roll < 0.93 ? 3 : 4;
    case "Hard":
      return roll < 0.28 ? 2 : roll < 0.66 ? 3 : 4;
    default:
      return 1;
  }
}

function pickLanguage(rng: Rng, problem: ProblemSeed, attemptNumber: number): Language {
  // The real seeded history is almost entirely Java; newer work is Python.
  const isSeeded = PROBLEM_SEEDS.slice(0, 21).some((seed) => seed.slug === problem.slug);
  if (isSeeded) {
    if (attemptNumber === 1) return chance(rng, 0.88) ? "Java" : pick(rng, LANGUAGES);
    return chance(rng, 0.55) ? "Java" : pick(rng, ["Python 3", "C++", "JavaScript", "Go"] as Language[]);
  }
  return pick(rng, LANGUAGES);
}

const NOTE_CONTENT: Record<ProblemNote["noteType"], string[]> = {
  Intuition: [
    "The constraint that the answer must be optimal is a hint that the naive scan is leaving structure on the table.",
    "Reframe it as: what does each element contribute to the final answer?",
  ],
  "Bug Pattern": [
    "I keep reaching for a nested loop before checking whether the data is already sorted.",
    "Edge case I forgot: an empty input should return the identity value, not throw.",
  ],
  "Complexity Analysis": [
    "Outer loop is O(n); the inner work is amortised to O(1) because each element is visited twice at most.",
    "Space is O(n) for the auxiliary map — there is no way to avoid it without losing the O(1) lookup.",
  ],
  General: [
    "Revisit this one in two weeks — the trick is easy to forget and it appears in many harder problems.",
    "Solved cleanly this time. Worth keeping as a template for the surrounding topic.",
  ],
};

function buildNotes(rng: Rng, problem: ProblemSeed, problemId: string, startDay: number): ProblemNote[] {
  if (!chance(rng, 0.42)) return [];
  const noteType = pick(rng, Object.keys(NOTE_CONTENT) as ProblemNote["noteType"][]);
  return [
    {
      id: `note_${hashId(problemId + noteType)}`,
      problemId,
      attemptId: null,
      content: pick(rng, NOTE_CONTENT[noteType]),
      noteType,
      createdAt: daysAgo(Math.max(0, startDay - 1)),
    },
  ];
}

/** Deterministic problem id so relationships and queues are stable. */
export function problemIdFor(slug: string): string {
  return `prob_${hashId(slug)}`;
}

let cached: Problem[] | null = null;

export function getMockProblems(): Problem[] {
  if (cached) return cached;

  const rng = createRng(0x4d3a);

  cached = PROBLEM_SEEDS.map((seed, index): Problem => {
    const id = problemIdFor(seed.slug);
    // Spread activity across ~120 days. The imported LeetCode archive sits at
    // the old end; the most recent work lands today or yesterday so the streak
    // reads as live. Jitter keeps the timeline non-monotone.
    const startDay =
      index === PROBLEM_SEEDS.length - 1
        ? intIn(rng, 0, 1)
        : Math.round((PROBLEM_SEEDS.length - 1 - index) * (120 / (PROBLEM_SEEDS.length - 1))) +
          intIn(rng, 0, 6);

    const attempts = buildAttempts(rng, seed, id, startDay);
    const firstSubmittedAt = attempts.reduce(
      (min, attempt) =>
        attempt.submissions[0] && attempt.submissions[0].submittedAt < min
          ? attempt.submissions[0].submittedAt
          : min,
      daysAgo(0),
    );

    return {
      id,
      title: seed.title,
      slug: seed.slug || slugify(seed.title),
      difficulty: seed.difficulty,
      platform: seed.platform ?? "LeetCode",
      url: `https://leetcode.com/problems/${seed.slug}/`,
      topics: seed.topics,
      statement: null,
      createdAt: firstSubmittedAt,
      updatedAt: attempts[attempts.length - 1]?.submissions[0]?.submittedAt ?? firstSubmittedAt,
      attempts,
      notes: buildNotes(rng, seed, id, startDay),
    };
  });

  return cached;
}
