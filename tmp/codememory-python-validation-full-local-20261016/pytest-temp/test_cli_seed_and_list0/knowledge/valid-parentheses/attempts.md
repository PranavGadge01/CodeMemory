# Attempts History: Valid Parentheses

## Attempt 1: Stack Matching
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Push opening brackets to stack; pop and match closing brackets.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `30.0 ms` | **Memory**: `14.8 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def isValid(s: str) -> bool:
    stack = []
    mp = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mp:
            top = stack.pop() if stack else '#'
            if mp[char] != top: return False
        else: stack.append(char)
    return not stack
```
