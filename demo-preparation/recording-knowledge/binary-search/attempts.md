# Attempts History: Binary Search

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:27 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `48.2 MB`
- **Timestamp**: `2026-03-21 13:59:52 UTC`

```java
class Solution {
    public int search(int[] nums, int target) {
        int low = 0, high = nums.length - 1;
        
        while(low <= high){
            int mid = (low + high) / 2;

            if(nums[mid] == target) return mid;
            else if(nums[mid] < target) low = mid + 1;
            else high = mid - 1;
        }

        return -1;
    }
}
```
