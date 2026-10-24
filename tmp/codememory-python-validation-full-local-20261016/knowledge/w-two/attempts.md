# Attempts History: W Two

## Attempt 1: Attempt
- **Status**: `Wrong Answer`
- **Date**: `2026-10-15 19:06:32 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-02 00:00:00 UTC`

```py
nums.sort()
left, right = 0, len(nums) - 1
while left < right:
    total = nums[left] + nums[right]
    if total == target:
        return [left, right]
    left += 1
return []
```
