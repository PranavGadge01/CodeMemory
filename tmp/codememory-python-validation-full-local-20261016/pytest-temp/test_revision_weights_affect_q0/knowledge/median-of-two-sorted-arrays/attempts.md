# Attempts History: Median of Two Sorted Arrays

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-26 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `52.0 ms` | **Memory**: `16.9 MB`
- **Timestamp**: `2024-01-26 09:00:00 UTC`

```py
class Solution:
    def findMedianSortedArrays(self, nums1, nums2):
        A, B = nums1, nums2
        if len(A) > len(B): A, B = B, A
        m, n = len(A), len(B)
        lo, hi = 0, m
        while lo <= hi:
            i = (lo + hi) // 2
            j = (m + n + 1) // 2 - i
            maxLeftA = float('-inf') if i == 0 else A[i-1]
            minRightA = float('inf') if i == m else A[i]
            maxLeftB = float('-inf') if j == 0 else B[j-1]
            minRightB = float('inf') if j == n else B[j]
            if maxLeftA <= minRightB and maxLeftB <= minRightA:
                if (m + n) % 2 == 0:
                    return (max(maxLeftA, maxLeftB) + min(minRightA, minRightB)) / 2
                else:
                    return max(maxLeftA, maxLeftB)
            elif maxLeftA > minRightB: hi = i - 1
            else: lo = i + 1
        return 0.0
```
