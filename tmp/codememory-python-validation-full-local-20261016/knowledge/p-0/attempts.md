# Attempts History: P 0

## Attempt 1: Attempt
- **Status**: `Wrong Answer`
- **Date**: `2026-10-15 19:06:32 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-01 00:00:00 UTC`

```py
seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []
```
