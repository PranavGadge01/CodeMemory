# Attempts History: Longest Substring Without Repeating Characters

## Attempt 1: Sliding Window with Hash Map
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Maintain left pointer and map of last seen indices.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(min(M, N))`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `55.0 ms` | **Memory**: `16.1 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def lengthOfLongestSubstring(s: str) -> int:
    seen = {}
    left = max_len = 0
    for right, char in enumerate(s):
        if char in seen and seen[char] >= left:
            left = seen[char] + 1
        seen[char] = right
        max_len = max(max_len, right - left + 1)
    return max_len
```
