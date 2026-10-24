# Attempts History: Valid Parentheses

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2023-11-18 09:33:20 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `28.0 ms` | **Memory**: `16.5 MB`
- **Timestamp**: `2023-11-18 09:33:20 UTC`

```py
class Solution:\n    def isValid(self, s: str) -> bool:\n        st = []\n        m = {')': '(', '}': '{', ']': '['}\n        for c in s:\n            if c in m:\n                if not st or st.pop() != m[c]: return False\n            else: st.append(c)\n        return not st
```
