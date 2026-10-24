# Attempts History: W One

## Attempt 1: Attempt
- **Status**: `Wrong Answer`
- **Date**: `2026-10-15 19:06:34 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
total = 0
for i in range(len(nums)):
    for j in range(len(nums)):
        if nums[i] + nums[j] == target:
            total += 1
return total
```
