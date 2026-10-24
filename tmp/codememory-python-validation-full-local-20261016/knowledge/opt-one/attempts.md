# Attempts History: Opt One

## Attempt 1: Attempt
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:06:32 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
total = 0
for i in range(len(nums)):
    for j in range(len(nums)):
        if nums[i] + nums[j] == target:
            total += 1
return total
```

## Attempt 2: Attempt
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:32 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `40.0 ms` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:01:00 UTC`

```py
seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []
```
