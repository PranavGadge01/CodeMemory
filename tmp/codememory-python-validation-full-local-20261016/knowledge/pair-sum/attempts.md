# Attempts History: Pair Sum

## Attempt 1: Attempt
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:44 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]

```
