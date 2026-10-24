# Attempts History: Generate Parentheses

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:29 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `45.0 MB`
- **Timestamp**: `2026-04-03 02:34:10 UTC`

```java
class Solution {
    private void build(int o, int c, List<String> res, String pattern) {
        if (o == 0 && c == 0) {
            res.add(pattern);
            return;
        }

        if (o > 0) {
            build(o - 1, c, res, pattern + "(");
        }

        if (c > o) {
            build(o, c - 1, res, pattern + ")");
        }
    }

    public List<String> generateParenthesis(int n) {
        List<String> res = new ArrayList<>();
        build(n, n, res, "");
        return res;
    }
}
```
