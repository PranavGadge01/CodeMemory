/**
 * Real solution code for the signature "solution evolution" stories.
 *
 * CodeMemory's core concept is that a problem is not one solution but a
 * progression — Attempt 1 brute force, Attempt 2 partial fix, then the
 * accepted optimal form. These snippets are shown in the code/diff views on
 * the home page and the problem detail panel.
 */

export interface EvolutionStep {
  attempt: number;
  approach: string;
  status: "Time Limit Exceeded" | "Wrong Answer" | "Accepted";
  language: string;
  timeComplexity: string;
  spaceComplexity: string;
  runtimeMs: number;
  code: string;
  note: string;
}

export interface EvolutionStory {
  slug: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  steps: EvolutionStep[];
  takeaway: string;
  betterApproach?: string;
  similarProblems?: string[];
}

export const EVOLUTION_STORIES: EvolutionStory[] = [
  {
    slug: "two-sum",
    title: "Two Sum",
    difficulty: "Easy",
    takeaway:
      "The hash map does not make the algorithm faster by doing less work — it removes the work that was never needed, the repeated lookup.",
    steps: [
      {
        attempt: 1,
        approach: "Brute Force",
        status: "Wrong Answer",
        language: "python3",
        timeComplexity: "O(n²)",
        spaceComplexity: "O(1)",
        runtimeMs: 3120,
        note: "Every pair is compared. Correct logic, but the loop bound was written as `range(i, n)` instead of `range(i + 1, n)`, so an element was paired with itself.",
        code: `class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        n = len(nums)
        for i in range(n):
            for j in range(i, n):          # bug: should be i + 1
                if nums[i] + nums[j] == target:
                    return [i, j]
        return []`,
      },
      {
        attempt: 2,
        approach: "Brute Force",
        status: "Time Limit Exceeded",
        language: "python3",
        timeComplexity: "O(n²)",
        spaceComplexity: "O(1)",
        runtimeMs: 2840,
        note: "Off-by-one fixed and accepted on small cases, but the quadratic scan times out once the array exceeds 10⁴ elements.",
        code: `class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        n = len(nums)
        for i in range(n):
            for j in range(i + 1, n):      # fixed
                if nums[i] + nums[j] == target:
                    return [i, j]
        return []`,
      },
      {
        attempt: 3,
        approach: "Hash Map Lookup",
        status: "Accepted",
        language: "python3",
        timeComplexity: "O(n)",
        spaceComplexity: "O(n)",
        runtimeMs: 52,
        note: "Store the complement of every element seen so far. One pass, no repeated scanning.",
        code: `class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen: dict[int, int] = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []`,
      },
    ],
  },
  {
    slug: "3sum",
    title: "3Sum",
    difficulty: "Medium",
    takeaway:
      "Sorting first converts a triple-nested scan into one pass plus a two-pointer contraction — the sort is the cheapest operation in the whole solution.",
    steps: [
      {
        attempt: 1,
        approach: "Brute Force",
        status: "Time Limit Exceeded",
        language: "java",
        timeComplexity: "O(n³)",
        spaceComplexity: "O(1)",
        runtimeMs: 8410,
        note: "Three nested loops over 3000 elements. Cubic growth has no chance against the time limit.",
        code: `class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        var result = new HashSet<List<Integer>>();
        int n = nums.length;
        for (int i = 0; i < n; i++)
            for (int j = i + 1; j < n; j++)
                for (int k = j + 1; k < n; k++)
                    if (nums[i] + nums[j] + nums[k] == 0)
                        result.add(sorted(nums[i], nums[j], nums[k]));
        return new ArrayList<>(result);
    }
}`,
      },
      {
        attempt: 2,
        approach: "Hash Map Lookup",
        status: "Wrong Answer",
        language: "java",
        timeComplexity: "O(n²)",
        spaceComplexity: "O(n)",
        runtimeMs: 690,
        note: "Dropped one loop with a complement set, but duplicates were only filtered after the fact, so identical triplets leaked into the output.",
        code: `class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        var result = new ArrayList<List<Integer>>();
        var seen = new HashSet<Integer>();
        for (int i = 0; i < nums.length; i++) {
            for (int j = i + 1; j < nums.length; j++) {
                int need = -(nums[i] + nums[j]);
                if (seen.contains(need))          // wrong window
                    result.add(List.of(nums[i], nums[j], need));
            }
            seen.add(nums[i]);
        }
        return result;
    }
}`,
      },
      {
        attempt: 3,
        approach: "Two Pointers",
        status: "Accepted",
        language: "java",
        timeComplexity: "O(n²)",
        spaceComplexity: "O(1)",
        runtimeMs: 31,
        note: "Sort, then contract two pointers around each anchor. Duplicates collapse naturally because equal neighbours are skipped.",
        code: `class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        Arrays.sort(nums);
        var result = new ArrayList<List<Integer>>();
        for (int i = 0; i < nums.length - 2; i++) {
            if (i > 0 && nums[i] == nums[i - 1]) continue;   // skip dup anchor
            int lo = i + 1, hi = nums.length - 1;
            while (lo < hi) {
                int sum = nums[i] + nums[lo] + nums[hi];
                if (sum == 0) {
                    result.add(List.of(nums[i], nums[lo], nums[hi]));
                    while (lo < hi && nums[lo] == nums[++lo]) ;
                    while (lo < hi && nums[hi] == nums[--hi]) ;
                } else if (sum < 0) lo++;
                else hi--;
            }
        }
        return result;
    }
}`,
      },
    ],
  },
  {
    slug: "trapping-rain-water",
    title: "Trapping Rain Water",
    difficulty: "Hard",
    takeaway:
      "Precomputing the tallest bar on each side turns a per-cell scan into two array lookups — the classic space-for-time trade that a later pass removes entirely.",
    steps: [
      {
        attempt: 1,
        approach: "Brute Force",
        status: "Time Limit Exceeded",
        language: "python3",
        timeComplexity: "O(n²)",
        spaceComplexity: "O(1)",
        runtimeMs: 5290,
        note: "For every index, scan outward to find the left and right maxima. Correct, but quadratic.",
        code: `class Solution:
    def trap(self, height: list[int]) -> int:
        water = 0
        for i in range(len(height)):
            left = max(height[:i + 1])
            right = max(height[i:])
            water += min(left, right) - height[i]
        return water`,
      },
      {
        attempt: 2,
        approach: "Dynamic Programming",
        status: "Accepted",
        language: "python3",
        timeComplexity: "O(n)",
        spaceComplexity: "O(n)",
        runtimeMs: 88,
        note: "Two prefix arrays carry the left and right maxima, so each cell is answered in constant time.",
        code: `class Solution:
    def trap(self, height: list[int]) -> int:
        n = len(height)
        left = [0] * n
        right = [0] * n
        left[0] = height[0]
        right[-1] = height[-1]
        for i in range(1, n):
            left[i] = max(left[i - 1], height[i])
        for i in range(n - 2, -1, -1):
            right[i] = max(right[i + 1], height[i])
        return sum(min(left[i], right[i]) - height[i] for i in range(n))`,
      },
      {
        attempt: 3,
        approach: "Two Pointers",
        status: "Accepted",
        language: "python3",
        timeComplexity: "O(n)",
        spaceComplexity: "O(1)",
        runtimeMs: 61,
        note: "Move the pointer from the shorter side — that side's maximum is already the binding constraint, so no precomputation is needed at all.",
        code: `class Solution:
    def trap(self, height: list[int]) -> int:
        lo, hi = 0, len(height) - 1
        left_max = right_max = water = 0
        while lo < hi:
            if height[lo] < height[hi]:
                left_max = max(left_max, height[lo])
                water += left_max - height[lo]
                lo += 1
            else:
                right_max = max(right_max, height[hi])
                water += right_max - height[hi]
                hi -= 1
        return water`,
      },
    ],
  },
];

export function getEvolutionStory(slug: string): EvolutionStory | null {
  return EVOLUTION_STORIES.find((story) => story.slug === slug) ?? null;
}

/** Runtime improvement across a story's steps, e.g. 3120 ms → 52 ms. */
export function evolutionImprovement(story: EvolutionStory): number {
  const first = story.steps[0];
  const last = story.steps[story.steps.length - 1];
  if (!first || !last) return 0;
  return Math.round((1 - last.runtimeMs / first.runtimeMs) * 100);
}
