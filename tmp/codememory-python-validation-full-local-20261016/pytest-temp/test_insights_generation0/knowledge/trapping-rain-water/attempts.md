# Attempts History: Trapping Rain Water

## Attempt 1: Two Pointers Max Left / Max Right
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Maintain left_max and right_max bounds moving l and r towards each other.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `110.0 ms` | **Memory**: `18.6 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
def trap(height: list[int]) -> int:
    if not height: return 0
    l, r = 0, len(height) - 1
    left_max, right_max = height[l], height[r]
    water = 0
    while l < r:
        if left_max < right_max:
            l += 1
            left_max = max(left_max, height[l])
            water += left_max - height[l]
        else:
            r -= 1
            right_max = max(right_max, height[r])
            water += right_max - height[r]
    return water
```
