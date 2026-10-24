# Attempts History: Two Sum

## Attempt 1: Attempt 1
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:06:17 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:06:17 UTC`

```py
def twoSum(nums, target):
 for i in range(len(nums)):
  for j in range(i+1, len(nums)):
   if nums[i]+nums[j]==target: return [i,j]
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:18 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `40.0 ms` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:06:18 UTC`

```py
def twoSum(nums, target):
 seen = {}
 for i, n in enumerate(nums):
  if target - n in seen: return [seen[target - n], i]
  seen[n] = i
```
