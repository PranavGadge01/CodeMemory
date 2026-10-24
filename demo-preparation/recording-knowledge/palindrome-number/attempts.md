# Attempts History: Palindrome Number

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:19 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `5.0 ms` | **Memory**: `45.7 MB`
- **Timestamp**: `2026-03-22 12:49:59 UTC`

```java
class Solution {
    public boolean isPalindrome(int x) {
        // Negative numbers OR numbers ending with 0 (except 0)
        if(x < 0 || (x % 10 == 0 && x != 0)) {
            return false;
        }

        int rev = 0;

        while(x > rev) {
            int digit = x % 10;
            rev = rev * 10 + digit;
            x /= 10;
        }

        // For even digits: x == rev
        // For odd digits: x == rev/10
        return (x == rev) || (x == rev / 10);
    }
}
```
