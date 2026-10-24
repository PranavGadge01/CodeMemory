# Attempts History: Move Zeroes

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:06 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `46.9 MB`
- **Timestamp**: `2026-03-24 17:40:34 UTC`

```java
class Solution {
    public void moveZeroes(int[] nums) {
        int insertPos = 0;

        for(int num : nums){
            if(num != 0){
                nums[insertPos++] = num;
            }
        }

        while(insertPos < nums.length){
            nums[insertPos++] = 0;
        }
    }
}
```
