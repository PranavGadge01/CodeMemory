# Attempts History: Two Sum

## Attempt 1: Attempt 1
- **Status**: `Wrong Answer`
- **Date**: `2024-01-10 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2024-01-10 09:00:00 UTC`

```py
class Solution:
    def twoSum(self, nums, target):
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                if nums[i]+nums[j]==target:
                    return [i,j]
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2024-01-10 10:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `45.0 ms` | **Memory**: `16.4 MB`
- **Timestamp**: `2024-01-10 10:00:00 UTC`

```py
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, n in enumerate(nums):
            diff = target - n
            if diff in seen:
                return [seen[diff], i]
            seen[n] = i
```
