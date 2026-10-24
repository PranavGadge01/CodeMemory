# Attempts History: Two Sum

## Attempt 1: Attempt
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:19:31 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
for i in range(len(nums)):
    for j in range(len(nums)):
        if nums[i] + nums[j] == target:
            return [i, j]
return []
```

## Attempt 2: Attempt
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:19:31 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-02 00:00:00 UTC`

```py
seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []
```
