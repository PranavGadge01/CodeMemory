# Attempts History: Median of Two Sorted Arrays

## Attempt 1: Binary Search on Partition Index
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Perform binary search on smaller array to find valid left/right partition cut.
- **Time Complexity**: `O(log(min(M, N)))`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `85.0 ms` | **Memory**: `16.5 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
def findMedianSortedArrays(nums1: list[int], nums2: list[int]) -> float:
    A, B = nums1, nums2
    total = len(A) + len(B)
    half = total // 2
    if len(B) < len(A): A, B = B, A
    l, r = 0, len(A) - 1
    while True:
        i = (l + r) // 2
        j = half - i - 2
        Aleft = A[i] if i >= 0 else float('-inf')
        Aright = A[i + 1] if (i + 1) < len(A) else float('inf')
        Bleft = B[j] if j >= 0 else float('-inf')
        Bright = B[j + 1] if (j + 1) < len(B) else float('inf')
        if Aleft <= Bright and Bleft <= Aright:
            if total % 2: return min(Aright, Bright)
            return (max(Aleft, Bleft) + min(Aright, Bright)) / 2
        elif Aleft > Bright: r = i - 1
        else: l = i + 1
```
