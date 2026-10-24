# Attempts History: Find Peak Element

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:11 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `44.2 MB`
- **Timestamp**: `2026-09-21 08:22:47 UTC`

```java
class Solution {
    public int findPeakElement(int[] nums) {
        int l = 0;
        int h =nums.length - 1;

        while(l<h){
            int mid = l + (h - l) / 2;

            if(nums[mid] < nums[mid + 1]){
                l = mid + 1;
            }else{
                h = mid;
            }
        }

        return h;
    }
}
```
