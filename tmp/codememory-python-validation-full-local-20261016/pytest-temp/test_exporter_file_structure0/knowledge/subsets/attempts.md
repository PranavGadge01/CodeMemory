# Attempts History: Subsets

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:34 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `35.0 ms` | **Memory**: `16.1 MB`
- **Timestamp**: `2026-10-15 19:06:34 UTC`

```py
def subsets(nums):
    res = [[]]
    for n in nums:
        res += [r + [n] for r in res]
    return res
```
