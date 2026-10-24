# Attempts History: Merge Intervals

## Attempt 1: Attempt 1
- **Status**: `Wrong Answer`
- **Date**: `2024-01-13 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2024-01-13 09:00:00 UTC`

```py
class Solution:
    def merge(self, intervals):
        intervals.sort()
        res = [intervals[0]]
        for s, e in intervals[1:]:
            if s > res[-1][1]:
                res.append([s, e])
        return res
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2024-01-13 11:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `72.0 ms` | **Memory**: `18.3 MB`
- **Timestamp**: `2024-01-13 11:00:00 UTC`

```py
class Solution:
    def merge(self, intervals):
        intervals.sort()
        res = [intervals[0]]
        for s, e in intervals[1:]:
            if s <= res[-1][1]:
                res[-1][1] = max(res[-1][1], e)
            else:
                res.append([s, e])
        return res
```
