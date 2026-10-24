# Attempts History: Remove Element

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:41 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `43.8 MB`
- **Timestamp**: `2026-03-20 16:45:29 UTC`

```java
class Solution {
    public int removeElement(int[] nums, int val) {
        int i = 0, n = nums.length;

        while(i < n){
            if(nums[i] == val){
                nums[i] = nums[n - 1];
                n--;
            } else {
                i++;
            }
        }

        return n;
    }
}
```
