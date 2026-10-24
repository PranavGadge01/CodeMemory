# Attempts History: Fibonacci Number

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:18 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `9.0 ms` | **Memory**: `42.2 MB`
- **Timestamp**: `2026-03-22 12:55:04 UTC`

```java
class Solution {
    public int fib(int n) {
        if(n <= 1) return n;

        return fib(n - 1) + fib(n - 2);
    }
}
```
