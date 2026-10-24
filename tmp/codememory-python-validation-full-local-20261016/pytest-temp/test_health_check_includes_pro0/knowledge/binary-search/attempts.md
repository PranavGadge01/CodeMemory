# Attempts History: Binary Search

## Attempt 1: Attempt 1
- **Status**: `Wrong Answer`
- **Date**: `2024-01-24 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2024-01-24 09:00:00 UTC`

```py
class Solution:
    def search(self, nums, target):
        lo, hi = 0, len(nums)
        while lo < hi:
            mid = (lo + hi) // 2
            if nums[mid] == target: return mid
            elif nums[mid] < target: lo = mid + 1
            else: hi = mid - 1
        return -1
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2024-01-24 10:30:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `38.0 ms` | **Memory**: `15.1 MB`
- **Timestamp**: `2024-01-24 10:30:00 UTC`

```py
class Solution:
    def search(self, nums, target):
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if nums[mid] == target: return mid
            elif nums[mid] < target: lo = mid + 1
            else: hi = mid - 1
        return -1
```
