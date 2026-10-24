# Attempts History: Find Peak Element

## Attempt 1: Attempt 1
- **Status**: `Wrong Answer`
- **Date**: `2026-10-15 19:06:35 UTC`
- **Reasoning**: Naive return zero index

### Submissions
#### Submission 1 (python)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:06:35 UTC`

```py
def findPeakElement(nums): return 0
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:35 UTC`
- **Reasoning**: Use max built-in

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `48.0 ms` | **Memory**: `16.0 MB`
- **Timestamp**: `2026-10-15 19:06:35 UTC`

```py
def findPeakElement(nums): return nums.index(max(nums))
```
