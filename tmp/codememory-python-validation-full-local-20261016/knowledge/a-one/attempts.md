# Attempts History: A One

## Attempt 1: Attempt
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:34 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []
```
