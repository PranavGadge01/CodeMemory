# Attempts History: Two Sum

## Attempt 1: Attempt 1
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:18:07 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:18:07 UTC`

```py
def twoSum(nums, target):
 for i in range(len(nums)):
  for j in range(i+1, len(nums)):
   if nums[i]+nums[j]==target: return [i,j]
```

## Attempt 2: Attempt 2
- **Status**: `Wrong Answer`
- **Date**: `2026-10-15 19:18:07 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:18:07 UTC`

```py
def twoSum(nums, target):
 hashmap = {}
 for i, n in enumerate(nums):
  if target - n in hashmap: return [hashmap[target], i]
  hashmap[n] = i
```

## Attempt 3: Attempt 3
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:18:08 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `45.0 ms` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:18:08 UTC`

```py
def twoSum(nums, target):
 hashmap = {}
 for i, n in enumerate(nums):
  if target - n in hashmap: return [hashmap[target - n], i]
  hashmap[n] = i
```
