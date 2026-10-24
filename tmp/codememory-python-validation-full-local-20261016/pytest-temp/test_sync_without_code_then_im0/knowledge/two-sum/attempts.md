# Attempts History: Two Sum

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:17:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `45.0 ms` | **Memory**: `17.2 MB`
- **Timestamp**: `2023-11-15 00:13:20 UTC`

```py

```

## Attempt 2: Attempt 2
- **Status**: `Wrong Answer`
- **Date**: `2023-11-14 22:13:20 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2023-11-14 22:13:20 UTC`

```py
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        return [0, 1]
```

## Attempt 3: Attempt 3
- **Status**: `Time Limit Exceeded`
- **Date**: `2023-11-14 23:13:20 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2023-11-14 23:13:20 UTC`

```py
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        for i in range(len(nums)):
            for j in range(len(nums)):
                if i != j and nums[i] + nums[j] == target:
                    return [i, j]
```

## Attempt 4: Attempt 4
- **Status**: `Accepted`
- **Date**: `2023-11-15 00:13:20 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `45.0 ms` | **Memory**: `17.2 MB`
- **Timestamp**: `2023-11-15 00:13:20 UTC`

```py
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, n in enumerate(nums):
            diff = target - n
            if diff in seen:
                return [seen[diff], i]
            seen[n] = i
```
