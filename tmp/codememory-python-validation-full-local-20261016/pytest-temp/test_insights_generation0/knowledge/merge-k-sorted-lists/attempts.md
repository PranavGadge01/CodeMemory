# Attempts History: Merge k Sorted Lists

## Attempt 1: Divide and Conquer Merge Pairs
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Merge lists pairwise repeatedly reducing total lists by half each iteration.
- **Time Complexity**: `O(N log K)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `90.0 ms` | **Memory**: `18.0 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
def mergeKLists(lists):
    if not lists: return None
    while len(lists) > 1:
        merged = []
        for i in range(0, len(lists), 2):
            l1 = lists[i]
            l2 = lists[i+1] if (i+1) < len(lists) else None
            merged.append(mergeTwo(l1, l2))
        lists = merged
    return lists[0]
```
