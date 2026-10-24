# Attempts History: Dp Two

## Attempt 1: Attempt
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:06:32 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-01-02 00:00:00 UTC`

```py
total = 0
for i in range(len(nums)):
    for j in range(len(nums)):
        if nums[i] + nums[j] == target:
            total += 1
return total
```
