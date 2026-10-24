# Attempts History: Plus One

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:26 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `43.7 MB`
- **Timestamp**: `2026-04-04 23:38:11 UTC`

```java
class Solution {
    public int[] plusOne(int[] digits) {
        int n = digits.length;

        for(int i = n - 1; i >= 0; i--) {
            if(digits[i] < 9) {
                digits[i]++;
                return digits;
            }
            digits[i] = 0;
        }

        // If all digits were 9
        int[] result = new int[n + 1];
        result[0] = 1;
        return result;
    }
}
```
