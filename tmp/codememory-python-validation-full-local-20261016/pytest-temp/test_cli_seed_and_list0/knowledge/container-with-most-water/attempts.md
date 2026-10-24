# Attempts History: Container With Most Water

## Attempt 1: Two Pointers Moving Inward
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Start with widest container and move the shorter pointer inward.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `140.0 ms` | **Memory**: `28.2 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def maxArea(height: list[int]) -> int:
    l, r = 0, len(height) - 1
    ans = 0
    while l < r:
        w = r - l
        h = min(height[l], height[r])
        ans = max(ans, w * h)
        if height[l] < height[r]: l += 1
        else: r -= 1
    return ans
```
