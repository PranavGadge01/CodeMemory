# Attempts History: Search in Rotated Sorted Array

## Attempt 1: Modified Binary Search
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:36 UTC`
- **Reasoning**: Determine which half of the rotated array is sorted at each step.
- **Time Complexity**: `O(log N)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:36 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `40.0 ms` | **Memory**: `16.5 MB`
- **Timestamp**: `2026-10-15 19:06:36 UTC`

```py
def search(nums: list[int], target: int) -> int:
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target: return mid
        if nums[l] <= nums[mid]:
            if nums[l] <= target < nums[mid]: r = mid - 1
            else: l = mid + 1
        else:
            if nums[mid] < target <= nums[r]: l = mid + 1
            else: r = mid - 1
    return -1
```
