# Attempts History: Longest Substring Without Repeating Characters

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-15 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `55.0 ms` | **Memory**: `14.8 MB`
- **Timestamp**: `2024-01-15 09:00:00 UTC`

```py
class Solution:
    def lengthOfLongestSubstring(self, s):
        seen = set()
        left = 0
        max_len = 0
        for right, c in enumerate(s):
            while c in seen:
                seen.remove(s[left])
                left += 1
            seen.add(c)
            max_len = max(max_len, right - left + 1)
        return max_len
```
