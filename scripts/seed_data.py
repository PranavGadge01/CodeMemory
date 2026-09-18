"""Seed data generator populating CodeMemory with 20+ realistic classic DSA problems and attempt histories."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Ensure src is in python path if script is run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel, Platform, SubmissionStatus


def seed_sample_data(service: CodeMemoryService | None = None) -> CodeMemoryService:
    """Populate database with 20+ sample DSA problems, attempts, submissions, and notes."""
    if service is None:
        service = CodeMemoryService()

    now = datetime.now(timezone.utc)

    # 1. Two Sum
    p1 = service.add_problem(
        title="Two Sum",
        difficulty=DifficultyLevel.EASY,
        topics=["Array", "Hash Table"],
        url="https://leetcode.com/problems/two-sum/",
        statement="Given an array of integers `nums` and an integer `target`, return indices of two numbers such that they add up to `target`.",
    )
    service.add_attempt(
        problem_identifier=p1.slug,
        approach_summary="Brute Force Double Loop",
        reasoning="Check all pairs of elements to find two numbers summing to target.",
        time_complexity="O(N^2)",
        space_complexity="O(1)",
        mistakes=["O(N^2) time complexity causes TLE on large arrays."],
    )
    service.add_submission(
        problem_identifier=p1.slug,
        code="def twoSum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target: return [i, j]\n    return []",
        language="python",
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
        runtime_ms=None,
        memory_mb=16.2,
        error_message="Time Limit Exceeded",
    )
    service.add_attempt(
        problem_identifier=p1.slug,
        approach_summary="One-pass Hash Map Lookups",
        reasoning="Store complement target - num in hash map while iterating over nums array.",
        time_complexity="O(N)",
        space_complexity="O(N)",
    )
    service.add_submission(
        problem_identifier=p1.slug,
        code="def twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        if target - num in seen: return [seen[target - num], i]\n        seen[num] = i\n    return []",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=45.0,
        memory_mb=16.4,
    )
    service.add_note(problem_identifier=p1.slug, content="Hash map provides O(1) average lookup time.")

    # 2. Reverse Linked List
    p2 = service.add_problem(
        title="Reverse Linked List",
        difficulty=DifficultyLevel.EASY,
        topics=["Linked List", "Recursion"],
        url="https://leetcode.com/problems/reverse-linked-list/",
        statement="Given the head of a singly linked list, reverse the list, and return the reversed list.",
    )
    service.add_attempt(
        problem_identifier=p2.slug,
        approach_summary="Iterative Three Pointers",
        reasoning="Maintain prev, curr, and nxt pointers to re-link nodes in place.",
        time_complexity="O(N)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p2.slug,
        code="def reverseList(head):\n    prev, curr = None, head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=32.0,
        memory_mb=15.2,
    )

    # 3. LRU Cache
    p3 = service.add_problem(
        title="LRU Cache",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Hash Table", "Linked List", "Design", "Doubly-Linked List"],
        url="https://leetcode.com/problems/lru-cache/",
        statement="Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.",
    )
    service.add_attempt(
        problem_identifier=p3.slug,
        approach_summary="Doubly Linked List + Hash Map",
        reasoning="Use hash map for O(1) key-to-node lookup and DLL for O(1) eviction/insertion.",
        time_complexity="O(1)",
        space_complexity="O(capacity)",
    )
    service.add_submission(
        problem_identifier=p3.slug,
        code="class LRUCache:\n    def __init__(self, capacity: int):\n        self.cap = capacity\n        self.cache = {}\n",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=120.0,
        memory_mb=75.4,
    )

    # 4. Binary Tree Level Order Traversal
    p4 = service.add_problem(
        title="Binary Tree Level Order Traversal",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Tree", "Breadth-First Search", "Binary Tree"],
        url="https://leetcode.com/problems/binary-tree-level-order-traversal/",
        statement="Given the root of a binary tree, return the level order traversal of its nodes' values.",
    )
    service.add_attempt(
        problem_identifier=p4.slug,
        approach_summary="BFS Queue Traversal",
        reasoning="Use deque to traverse tree level by level.",
        time_complexity="O(N)",
        space_complexity="O(N)",
    )
    service.add_submission(
        problem_identifier=p4.slug,
        code="from collections import deque\ndef levelOrder(root):\n    if not root: return []\n    q = deque([root]); res = []\n    while q:\n        level = []\n        for _ in range(len(q)):\n            n = q.popleft(); level.append(n.val)\n            if n.left: q.append(n.left)\n            if n.right: q.append(n.right)\n        res.append(level)\n    return res",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=42.0,
        memory_mb=17.0,
    )

    # 5. Longest Substring Without Repeating Characters
    p5 = service.add_problem(
        title="Longest Substring Without Repeating Characters",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Hash Table", "String", "Sliding Window"],
        url="https://leetcode.com/problems/longest-substring-without-repeating-characters/",
        statement="Given a string s, find the length of the longest substring without repeating characters.",
    )
    service.add_attempt(
        problem_identifier=p5.slug,
        approach_summary="Sliding Window with Hash Map",
        reasoning="Maintain left pointer and map of last seen indices.",
        time_complexity="O(N)",
        space_complexity="O(min(M, N))",
    )
    service.add_submission(
        problem_identifier=p5.slug,
        code="def lengthOfLongestSubstring(s: str) -> int:\n    seen = {}\n    left = max_len = 0\n    for right, char in enumerate(s):\n        if char in seen and seen[char] >= left:\n            left = seen[char] + 1\n        seen[char] = right\n        max_len = max(max_len, right - left + 1)\n    return max_len",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=55.0,
        memory_mb=16.1,
    )

    # 6. Container With Most Water
    p6 = service.add_problem(
        title="Container With Most Water",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Two Pointers", "Greedy"],
        url="https://leetcode.com/problems/container-with-most-water/",
        statement="Given n non-negative integers height where each represents a point at coordinate (i, height[i]), find two lines that form a container storing the most water.",
    )
    service.add_attempt(
        problem_identifier=p6.slug,
        approach_summary="Two Pointers Moving Inward",
        reasoning="Start with widest container and move the shorter pointer inward.",
        time_complexity="O(N)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p6.slug,
        code="def maxArea(height: list[int]) -> int:\n    l, r = 0, len(height) - 1\n    ans = 0\n    while l < r:\n        w = r - l\n        h = min(height[l], height[r])\n        ans = max(ans, w * h)\n        if height[l] < height[r]: l += 1\n        else: r -= 1\n    return ans",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=140.0,
        memory_mb=28.2,
    )

    # 7. 3Sum
    p7 = service.add_problem(
        title="3Sum",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Two Pointers", "Sorting"],
        url="https://leetcode.com/problems/3sum/",
        statement="Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0.",
    )
    service.add_attempt(
        problem_identifier=p7.slug,
        approach_summary="Sort + Two Pointers",
        reasoning="Sort array first, iterate first element, use two pointers for remaining target sum.",
        time_complexity="O(N^2)",
        space_complexity="O(1)",
        mistakes=["Duplicate triplets generated when not skipping duplicate elements."],
    )
    service.add_submission(
        problem_identifier=p7.slug,
        code="def threeSum(nums: list[int]) -> list[list[int]]:\n    nums.sort()\n    res = []\n    for i in range(len(nums) - 2):\n        if i > 0 and nums[i] == nums[i-1]: continue\n        l, r = i + 1, len(nums) - 1\n        while l < r:\n            s = nums[i] + nums[l] + nums[r]\n            if s < 0: l += 1\n            elif s > 0: r -= 1\n            else:\n                res.append([nums[i], nums[l], nums[r]])\n                while l < r and nums[l] == nums[l+1]: l += 1\n                while l < r and nums[r] == nums[r-1]: r -= 1\n                l += 1; r -= 1\n    return res",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=180.0,
        memory_mb=19.5,
    )

    # 8. Valid Parentheses
    p8 = service.add_problem(
        title="Valid Parentheses",
        difficulty=DifficultyLevel.EASY,
        topics=["String", "Stack"],
        url="https://leetcode.com/problems/valid-parentheses/",
        statement="Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
    )
    service.add_attempt(
        problem_identifier=p8.slug,
        approach_summary="Stack Matching",
        reasoning="Push opening brackets to stack; pop and match closing brackets.",
        time_complexity="O(N)",
        space_complexity="O(N)",
    )
    service.add_submission(
        problem_identifier=p8.slug,
        code="def isValid(s: str) -> bool:\n    stack = []\n    mp = {')': '(', '}': '{', ']': '['}\n    for char in s:\n        if char in mp:\n            top = stack.pop() if stack else '#'\n            if mp[char] != top: return False\n        else: stack.append(char)\n    return not stack",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=30.0,
        memory_mb=14.8,
    )

    # 9. Merge Two Sorted Lists
    p9 = service.add_problem(
        title="Merge Two Sorted Lists",
        difficulty=DifficultyLevel.EASY,
        topics=["Linked List", "Recursion"],
        url="https://leetcode.com/problems/merge-two-sorted-lists/",
        statement="Merge two sorted linked lists into one sorted list.",
    )
    service.add_attempt(
        problem_identifier=p9.slug,
        approach_summary="Dummy Node Iterative Merge",
        reasoning="Compare heads of list1 and list2, appending smaller node to dummy tail.",
        time_complexity="O(N + M)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p9.slug,
        code="def mergeTwoLists(l1, l2):\n    dummy = curr = ListNode(0)\n    while l1 and l2:\n        if l1.val < l2.val:\n            curr.next, l1 = l1, l1.next\n        else:\n            curr.next, l2 = l2, l2.next\n        curr = curr.next\n    curr.next = l1 or l2\n    return dummy.next",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=38.0,
        memory_mb=15.0,
    )

    # 10. Maximum Subarray
    p10 = service.add_problem(
        title="Maximum Subarray",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Divide and Conquer", "Dynamic Programming"],
        url="https://leetcode.com/problems/maximum-subarray/",
        statement="Given an integer array nums, find the subarray with the largest sum, and return its sum.",
    )
    service.add_attempt(
        problem_identifier=p10.slug,
        approach_summary="Kadane's Algorithm",
        reasoning="Track max sub-sum ending at current index: curr = max(num, curr + num).",
        time_complexity="O(N)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p10.slug,
        code="def maxSubArray(nums: list[int]) -> int:\n    max_sum = curr_sum = nums[0]\n    for num in nums[1:]:\n        curr_sum = max(num, curr_sum + num)\n        max_sum = max(max_sum, curr_sum)\n    return max_sum",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=65.0,
        memory_mb=28.4,
    )

    # 11. Search in Rotated Sorted Array
    p11 = service.add_problem(
        title="Search in Rotated Sorted Array",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Binary Search"],
        url="https://leetcode.com/problems/search-in-rotated-sorted-array/",
        statement="Given the array nums after the possible rotation and an integer target, return the index of target if it is in nums.",
    )
    service.add_attempt(
        problem_identifier=p11.slug,
        approach_summary="Modified Binary Search",
        reasoning="Determine which half of the rotated array is sorted at each step.",
        time_complexity="O(log N)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p11.slug,
        code="def search(nums: list[int], target: int) -> int:\n    l, r = 0, len(nums) - 1\n    while l <= r:\n        mid = (l + r) // 2\n        if nums[mid] == target: return mid\n        if nums[l] <= nums[mid]:\n            if nums[l] <= target < nums[mid]: r = mid - 1\n            else: l = mid + 1\n        else:\n            if nums[mid] < target <= nums[r]: l = mid + 1\n            else: r = mid - 1\n    return -1",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=40.0,
        memory_mb=16.5,
    )

    # 12. Coin Change
    p12 = service.add_problem(
        title="Coin Change",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Dynamic Programming", "Breadth-First Search"],
        url="https://leetcode.com/problems/coin-change/",
        statement="Return the fewest number of coins that you need to make up that amount.",
    )
    service.add_attempt(
        problem_identifier=p12.slug,
        approach_summary="Bottom-Up DP",
        reasoning="dp[i] stores min coins to form amount i: dp[i] = min(dp[i], dp[i - coin] + 1).",
        time_complexity="O(amount * len(coins))",
        space_complexity="O(amount)",
    )
    service.add_submission(
        problem_identifier=p12.slug,
        code="def coinChange(coins: list[int], amount: int) -> int:\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for coin in coins:\n        for i in range(coin, amount + 1):\n            dp[i] = min(dp[i], dp[i - coin] + 1)\n    return dp[amount] if dp[amount] != float('inf') else -1",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=650.0,
        memory_mb=16.8,
    )

    # 13. Number of Islands
    p13 = service.add_problem(
        title="Number of Islands",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Depth-First Search", "Breadth-First Search", "Union Find", "Matrix"],
        url="https://leetcode.com/problems/number-of-islands/",
        statement="Given an m x n 2D binary grid grid which represents a map of '1's (land) and '0's (water), return the number of islands.",
    )
    service.add_attempt(
        problem_identifier=p13.slug,
        approach_summary="Grid DFS Traversal",
        reasoning="Traverse 2D matrix; when land '1' encountered, increment island count and DFS sink all connected '1's.",
        time_complexity="O(M * N)",
        space_complexity="O(M * N)",
    )
    service.add_submission(
        problem_identifier=p13.slug,
        code="def numIslands(grid: list[list[str]]) -> int:\n    if not grid: return 0\n    rows, cols = len(grid), len(grid[0])\n    count = 0\n    def dfs(r, c):\n        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] != '1': return\n        grid[r][c] = '0'\n        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == '1':\n                count += 1\n                dfs(r, c)\n    return count",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=210.0,
        memory_mb=32.1,
    )

    # 14. Course Schedule
    p14 = service.add_problem(
        title="Course Schedule",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Depth-First Search", "Breadth-First Search", "Graph", "Topological Sort"],
        url="https://leetcode.com/problems/course-schedule/",
        statement="Return true if you can finish all courses. Otherwise, return false.",
    )
    service.add_attempt(
        problem_identifier=p14.slug,
        approach_summary="Kahn's Algorithm (Topological Sort BFS)",
        reasoning="Track in-degrees of nodes; process 0 in-degree nodes via BFS queue.",
        time_complexity="O(V + E)",
        space_complexity="O(V + E)",
    )
    service.add_submission(
        problem_identifier=p14.slug,
        code="from collections import deque\ndef canFinish(numCourses: int, prerequisites: list[list[int]]) -> bool:\n    adj = [[] for _ in range(numCourses)]\n    indegree = [0] * numCourses\n    for crs, pre in prerequisites:\n        adj[pre].append(crs)\n        indegree[crs] += 1\n    q = deque([i for i in range(numCourses) if indegree[i] == 0])\n    visited = 0\n    while q:\n        node = q.popleft()\n        visited += 1\n        for nxt in adj[node]:\n            indegree[nxt] -= 1\n            if indegree[nxt] == 0: q.append(nxt)\n    return visited == numCourses",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=85.0,
        memory_mb=17.5,
    )

    # 15. Word Break
    p15 = service.add_problem(
        title="Word Break",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Hash Table", "String", "Dynamic Programming", "Trie", "Memoization"],
        url="https://leetcode.com/problems/word-break/",
        statement="Given a string s and a dictionary of strings wordDict, return true if s can be segmented into space-separated sequence of dictionary words.",
    )
    service.add_attempt(
        problem_identifier=p15.slug,
        approach_summary="1D DP Array",
        reasoning="dp[i] represents whether s[:i] can be segmented into words in wordDict.",
        time_complexity="O(N^2 * M)",
        space_complexity="O(N)",
    )
    service.add_submission(
        problem_identifier=p15.slug,
        code="def wordBreak(s: str, wordDict: list[str]) -> bool:\n    words = set(wordDict)\n    dp = [False] * (len(s) + 1)\n    dp[0] = True\n    for i in range(1, len(s) + 1):\n        for j in range(i):\n            if dp[j] and s[j:i] in words:\n                dp[i] = True\n                break\n    return dp[len(s)]",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=40.0,
        memory_mb=16.2,
    )

    # 16. Kth Largest Element in an Array
    p16 = service.add_problem(
        title="Kth Largest Element in an Array",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Divide and Conquer", "Sorting", "Heap (Priority Queue)", "Quickselect"],
        url="https://leetcode.com/problems/kth-largest-element-in-an-array/",
        statement="Given an integer array nums and an integer k, return the kth largest element in the array.",
    )
    service.add_attempt(
        problem_identifier=p16.slug,
        approach_summary="Min Heap of Size K",
        reasoning="Maintain min heap of size k; top element will be kth largest.",
        time_complexity="O(N log K)",
        space_complexity="O(K)",
    )
    service.add_submission(
        problem_identifier=p16.slug,
        code="import heapq\ndef findKthLargest(nums: list[int], k: int) -> int:\n    heap = []\n    for num in nums:\n        heapq.heappush(heap, num)\n        if len(heap) > k:\n            heapq.heappop(heap)\n    return heap[0]",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=450.0,
        memory_mb=27.0,
    )

    # 17. Subsets
    p17 = service.add_problem(
        title="Subsets",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Array", "Backtracking", "Bit Manipulation"],
        url="https://leetcode.com/problems/subsets/",
        statement="Given an integer array nums of unique elements, return all possible subsets (the power set).",
    )
    service.add_attempt(
        problem_identifier=p17.slug,
        approach_summary="Backtracking Decision Tree",
        reasoning="At each element index, decide whether to include element or skip.",
        time_complexity="O(2^N)",
        space_complexity="O(N)",
    )
    service.add_submission(
        problem_identifier=p17.slug,
        code="def subsets(nums: list[int]) -> list[list[int]]:\n    res = []\n    def backtrack(idx, path):\n        if idx == len(nums):\n            res.append(path[:]); return\n        backtrack(idx + 1, path + [nums[idx]])\n        backtrack(idx + 1, path)\n    backtrack(0, [])\n    return res",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=35.0,
        memory_mb=16.4,
    )

    # 18. Cloned Graph (Clone Graph)
    p18 = service.add_problem(
        title="Clone Graph",
        difficulty=DifficultyLevel.MEDIUM,
        topics=["Hash Table", "Depth-First Search", "Breadth-First Search", "Graph"],
        url="https://leetcode.com/problems/clone-graph/",
        statement="Given a reference of a node in a connected undirected graph, return a deep copy (clone) of the graph.",
    )
    service.add_attempt(
        problem_identifier=p18.slug,
        approach_summary="DFS with Hash Map Tracker",
        reasoning="Map original node to cloned node to handle cycles cleanly during DFS.",
        time_complexity="O(V + E)",
        space_complexity="O(V)",
    )
    service.add_submission(
        problem_identifier=p18.slug,
        code="def cloneGraph(node):\n    if not node: return None\n    old_to_new = {}\n    def dfs(n):\n        if n in old_to_new: return old_to_new[n]\n        copy = Node(n.val)\n        old_to_new[n] = copy\n        for nei in n.neighbors:\n            copy.neighbors.append(dfs(nei))\n        return copy\n    return dfs(node)",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=42.0,
        memory_mb=16.7,
    )

    # 19. Trapping Rain Water
    p19 = service.add_problem(
        title="Trapping Rain Water",
        difficulty=DifficultyLevel.HARD,
        topics=["Array", "Two Pointers", "Dynamic Programming", "Stack", "Monotonic Stack"],
        url="https://leetcode.com/problems/trapping-rain-water/",
        statement="Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.",
    )
    service.add_attempt(
        problem_identifier=p19.slug,
        approach_summary="Two Pointers Max Left / Max Right",
        reasoning="Maintain left_max and right_max bounds moving l and r towards each other.",
        time_complexity="O(N)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p19.slug,
        code="def trap(height: list[int]) -> int:\n    if not height: return 0\n    l, r = 0, len(height) - 1\n    left_max, right_max = height[l], height[r]\n    water = 0\n    while l < r:\n        if left_max < right_max:\n            l += 1\n            left_max = max(left_max, height[l])\n            water += left_max - height[l]\n        else:\n            r -= 1\n            right_max = max(right_max, height[r])\n            water += right_max - height[r]\n    return water",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=110.0,
        memory_mb=18.6,
    )

    # 20. Median of Two Sorted Arrays
    p20 = service.add_problem(
        title="Median of Two Sorted Arrays",
        difficulty=DifficultyLevel.HARD,
        topics=["Array", "Binary Search", "Divide and Conquer"],
        url="https://leetcode.com/problems/median-of-two-sorted-arrays/",
        statement="Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.",
    )
    service.add_attempt(
        problem_identifier=p20.slug,
        approach_summary="Binary Search on Partition Index",
        reasoning="Perform binary search on smaller array to find valid left/right partition cut.",
        time_complexity="O(log(min(M, N)))",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p20.slug,
        code="def findMedianSortedArrays(nums1: list[int], nums2: list[int]) -> float:\n    A, B = nums1, nums2\n    total = len(A) + len(B)\n    half = total // 2\n    if len(B) < len(A): A, B = B, A\n    l, r = 0, len(A) - 1\n    while True:\n        i = (l + r) // 2\n        j = half - i - 2\n        Aleft = A[i] if i >= 0 else float('-inf')\n        Aright = A[i + 1] if (i + 1) < len(A) else float('inf')\n        Bleft = B[j] if j >= 0 else float('-inf')\n        Bright = B[j + 1] if (j + 1) < len(B) else float('inf')\n        if Aleft <= Bright and Bleft <= Aright:\n            if total % 2: return min(Aright, Bright)\n            return (max(Aleft, Bleft) + min(Aright, Bright)) / 2\n        elif Aleft > Bright: r = i - 1\n        else: l = i + 1",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=85.0,
        memory_mb=16.5,
    )

    # 21. Merge K Sorted Lists
    p21 = service.add_problem(
        title="Merge k Sorted Lists",
        difficulty=DifficultyLevel.HARD,
        topics=["Linked List", "Divide and Conquer", "Heap (Priority Queue)", "Merge Sort"],
        url="https://leetcode.com/problems/merge-k-sorted-lists/",
        statement="You are given an array of k linked-lists lists, each linked-list is sorted in ascending order. Merge all the linked-lists into one sorted linked-list and return it.",
    )
    service.add_attempt(
        problem_identifier=p21.slug,
        approach_summary="Divide and Conquer Merge Pairs",
        reasoning="Merge lists pairwise repeatedly reducing total lists by half each iteration.",
        time_complexity="O(N log K)",
        space_complexity="O(1)",
    )
    service.add_submission(
        problem_identifier=p21.slug,
        code="def mergeKLists(lists):\n    if not lists: return None\n    while len(lists) > 1:\n        merged = []\n        for i in range(0, len(lists), 2):\n            l1 = lists[i]\n            l2 = lists[i+1] if (i+1) < len(lists) else None\n            merged.append(mergeTwo(l1, l2))\n        lists = merged\n    return lists[0]",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=90.0,
        memory_mb=18.0,
    )

    # 22. Word Search II
    p22 = service.add_problem(
        title="Word Search II",
        difficulty=DifficultyLevel.HARD,
        topics=["Array", "String", "Backtracking", "Trie", "Matrix"],
        url="https://leetcode.com/problems/word-search-ii/",
        statement="Given an m x n board of characters and a list of strings words, return all words on the board.",
    )
    service.add_attempt(
        problem_identifier=p22.slug,
        approach_summary="Trie-based Backtracking DFS",
        reasoning="Construct Trie of words and prune invalid search branches early during board DFS.",
        time_complexity="O(M * N * 4^L)",
        space_complexity="O(SUM(len(word)))",
    )
    service.add_submission(
        problem_identifier=p22.slug,
        code="class TrieNode:\n    def __init__(self):\n        self.children = {}\n        self.is_word = False\n",
        language="python",
        status=SubmissionStatus.ACCEPTED,
        runtime_ms=1200.0,
        memory_mb=35.0,
    )

    # Export knowledge base automatically
    service.export_knowledge()
    return service


if __name__ == "__main__":
    seed_sample_data()
    print("Successfully seeded 22 realistic DSA problems and attempt histories!")
