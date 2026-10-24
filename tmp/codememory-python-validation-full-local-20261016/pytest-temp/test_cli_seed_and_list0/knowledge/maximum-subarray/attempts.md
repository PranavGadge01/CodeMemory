# Attempts History: Maximum Subarray

## Attempt 1: Kadane's Algorithm
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Track max sub-sum ending at current index: curr = max(num, curr + num).
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `65.0 ms` | **Memory**: `28.4 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def maxSubArray(nums: list[int]) -> int:
    max_sum = curr_sum = nums[0]
    for num in nums[1:]:
        curr_sum = max(num, curr_sum + num)
        max_sum = max(max_sum, curr_sum)
    return max_sum
```
