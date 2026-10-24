# Attempts History: 3Sum

## Attempt 1: Attempt 1
- **Status**: `Time Limit Exceeded`
- **Date**: `2024-01-16 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2024-01-16 09:00:00 UTC`

```py
class Solution:
    def threeSum(self, nums):
        nums.sort()
        res = []
        for i in range(len(nums) - 2):
            if i > 0 and nums[i] == nums[i-1]:
                continue
            l, r = i+1, len(nums)-1
            while l < r:
                total = nums[i] + nums[l] + nums[r]
                if total == 0:
                    res.append([nums[i], nums[l], nums[r]])
                    while l < r and nums[l] == nums[l+1]: l += 1
                    while l < r and nums[r] == nums[r-1]: r -= 1
                    l += 1; r -= 1
                elif total < 0: l += 1
                else: r -= 1
        return res
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2024-01-16 14:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `320.0 ms` | **Memory**: `20.1 MB`
- **Timestamp**: `2024-01-16 14:00:00 UTC`

```py
class Solution:
    def threeSum(self, nums):
        nums.sort()
        res = []
        for i in range(len(nums) - 2):
            if nums[i] > 0: break
            if i > 0 and nums[i] == nums[i-1]: continue
            l, r = i+1, len(nums)-1
            while l < r:
                total = nums[i] + nums[l] + nums[r]
                if total == 0:
                    res.append([nums[i], nums[l], nums[r]])
                    while l < r and nums[l] == nums[l+1]: l += 1
                    while l < r and nums[r] == nums[r-1]: r -= 1
                    l += 1; r -= 1
                elif total < 0: l += 1
                else: r -= 1
        return res
```
