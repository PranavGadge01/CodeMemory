# Attempts History: Median of Two Sorted Arrays

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:45 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `48.8 MB`
- **Timestamp**: `2026-03-20 12:28:16 UTC`

```java
class Solution {
    public double findMedianSortedArrays(int[] nums1, int[] nums2) {
        int m = nums1.length;
        int n = nums2.length;

        if(m > n){
            return findMedianSortedArrays(nums2, nums1);
        }

        int low = 0, high = m;
        int left = (m + n + 1) / 2; 
        int totalLen = m + n;
        
        while(low <= high){
            int mid1 = (low + high) / 2;
            int mid2 = left - mid1;

            int l1 = Integer.MIN_VALUE, l2 = Integer.MIN_VALUE;
            int r1 = Integer.MAX_VALUE, r2 = Integer.MAX_VALUE;

            if(mid1 < m) r1 = nums1[mid1];
            if(mid2 < n) r2 = nums2[mid2];

            if((mid1 - 1) >= 0) l1 = nums1[mid1 - 1];
            if((mid2 - 1) >= 0) l2 = nums2[mid2 - 1];

            if(l1 <= r2 && l2 <= r1){
                if(totalLen % 2 == 0){
                    return ((double) Math.max(l1, l2) + Math.min(r1, r2)) / 2.0;
                }else{
                    return Math.max(l1, l2);
                }
            }
            else if(l1 > r2) high = mid1 - 1;
            else low = mid1 + 1;
        }
        
        return 0;
    }
}
```
