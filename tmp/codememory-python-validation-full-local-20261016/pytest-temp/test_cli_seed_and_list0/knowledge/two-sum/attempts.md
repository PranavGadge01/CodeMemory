# Attempts History: Two Sum

## Attempt 1: Brute Force Double Loop
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:28 UTC`
- **Reasoning**: Check all pairs of elements to find two numbers summing to target.
- **Time Complexity**: `O(N^2)`
- **Space Complexity**: `O(1)`
- **Mistakes / Lessons**: O(N^2) time complexity causes TLE on large arrays.

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: One-pass Hash Map Lookups
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:28 UTC`
- **Reasoning**: Store complement target - num in hash map while iterating over nums array.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:06:28 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `16.2 MB`
- **Timestamp**: `2026-10-15 19:06:28 UTC`
- **Error Message**: `Time Limit Exceeded`

```py
def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            if nums[i] + nums[j] == target: return [i, j]
    return []
```

## Attempt 4: Attempt 4
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:28 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `45.0 ms` | **Memory**: `16.4 MB`
- **Timestamp**: `2026-10-15 19:06:28 UTC`

```py
def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen: return [seen[target - num], i]
        seen[num] = i
    return []
```
