# Attempts History: Reverse Integer

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:21 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `42.7 MB`
- **Timestamp**: `2026-03-22 12:39:59 UTC`

```java
class Solution {
    public int reverse(int x) {
        long result = 0;

        while(x != 0){
            int lastDigit = x % 10;
            result = (result * 10) + lastDigit;

            x = x / 10;
        }

        if(result > Integer.MAX_VALUE || result < Integer.MIN_VALUE){
            return 0;
        }

        return (int) result;
    }
}
```
