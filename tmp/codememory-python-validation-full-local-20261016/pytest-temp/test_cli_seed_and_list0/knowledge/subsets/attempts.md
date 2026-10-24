# Attempts History: Subsets

## Attempt 1: Backtracking Decision Tree
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:30 UTC`
- **Reasoning**: At each element index, decide whether to include element or skip.
- **Time Complexity**: `O(2^N)`
- **Space Complexity**: `O(N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:30 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `35.0 ms` | **Memory**: `16.4 MB`
- **Timestamp**: `2026-10-15 19:06:30 UTC`

```py
def subsets(nums: list[int]) -> list[list[int]]:
    res = []
    def backtrack(idx, path):
        if idx == len(nums):
            res.append(path[:]); return
        backtrack(idx + 1, path + [nums[idx]])
        backtrack(idx + 1, path)
    backtrack(0, [])
    return res
```
