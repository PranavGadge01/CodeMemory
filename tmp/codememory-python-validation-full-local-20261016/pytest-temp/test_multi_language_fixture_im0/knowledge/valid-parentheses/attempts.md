# Attempts History: Valid Parentheses

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-12 10:00:00 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `40.2 MB`
- **Timestamp**: `2024-01-12 10:00:00 UTC`

```java
class Solution {
    public boolean isValid(String s) {
        Stack<Character> stack = new Stack<>();
        for (char c : s.toCharArray()) {
            if (c == '(' || c == '[' || c == '{') stack.push(c);
            else if (stack.isEmpty()) return false;
            else if (c == ')' && stack.pop() != '(') return false;
            else if (c == ']' && stack.pop() != '[') return false;
            else if (c == '}' && stack.pop() != '{') return false;
        }
        return stack.isEmpty();
    }
}
```
