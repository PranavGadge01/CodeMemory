# Attempts History: 3Sum

## Attempt 1: Sort + Two Pointers
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Sort array first, iterate first element, use two pointers for remaining target sum.
- **Time Complexity**: `O(N^2)`
- **Space Complexity**: `O(1)`
- **Mistakes / Lessons**: Duplicate triplets generated when not skipping duplicate elements.

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `180.0 ms` | **Memory**: `19.5 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def threeSum(nums: list[int]) -> list[list[int]]:
    nums.sort()
    res = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]: continue
        l, r = i + 1, len(nums) - 1
        while l < r:
            s = nums[i] + nums[l] + nums[r]
            if s < 0: l += 1
            elif s > 0: r -= 1
            else:
                res.append([nums[i], nums[l], nums[r]])
                while l < r and nums[l] == nums[l+1]: l += 1
                while l < r and nums[r] == nums[r-1]: r -= 1
                l += 1; r -= 1
    return res
```
