# Attempts History: Valid Parentheses

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:34 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `2.0 ms` | **Memory**: `43.4 MB`
- **Timestamp**: `2026-03-21 06:23:33 UTC`

```java
import java.util.Deque;
import java.util.ArrayDeque;

class Solution {
    public boolean isValid(String s) {
        Deque<Character> stack = new ArrayDeque<>();

        for(char ch : s.toCharArray()){
            if(ch == '(') stack.push(')');
            else if(ch == '[') stack.push(']');
            else if(ch == '{') stack.push('}');
            else {
                if(stack.isEmpty() || stack.pop() != ch){
                    return false;
                }
            }
        }

        return stack.isEmpty();
    }
}
```
