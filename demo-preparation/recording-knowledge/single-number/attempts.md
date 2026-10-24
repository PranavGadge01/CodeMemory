# Attempts History: Single Number

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:10 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `47.2 MB`
- **Timestamp**: `2026-03-24 16:59:07 UTC`

```java
class Solution {
    public int singleNumber(int[] nums) {
        int xor = 0;
        int n = nums.length;

        for(int i = 0; i < n; i++ ){
            xor = xor ^ nums[i];
        }

        return xor;
    }
}
```
