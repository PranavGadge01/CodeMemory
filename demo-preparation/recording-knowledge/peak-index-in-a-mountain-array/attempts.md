# Attempts History: Peak Index in a Mountain Array

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:10 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `78.6 MB`
- **Timestamp**: `2026-09-21 08:36:09 UTC`

```java
class Solution {
    public int peakIndexInMountainArray(int[] nums) {
        int l = 0;
        int h = nums.length - 1;

        while (l < h) {
            int mid = l + (h - l) / 2;

            if (nums[mid] < nums[mid + 1]) {
                l = mid + 1;
            } else {
                h = mid;
            }
        }
        return h;
    }
}
```
