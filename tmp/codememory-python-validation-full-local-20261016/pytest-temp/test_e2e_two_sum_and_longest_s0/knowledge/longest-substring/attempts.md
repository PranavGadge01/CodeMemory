# Attempts History: Longest Substring Without Repeating Characters

## Attempt 1: Attempt 1
- **Status**: `Time Limit Exceeded`
- **Date**: `2026-10-15 19:18:08 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Time Limit Exceeded` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:18:08 UTC`

```py
def lengthOfLongestSubstring(s):
 for i in range(len(s)):
  for j in range(i, len(s)):
   if len(set(s[i:j])) != j-i: pass
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:18:08 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `55.0 ms` | **Memory**: `N/A`
- **Timestamp**: `2026-10-15 19:18:08 UTC`

```py
def lengthOfLongestSubstring(s):
 char_map = {}
 left = max_len = 0
 for right, char in enumerate(s):
  if char in char_map and char_map[char] >= left: left = char_map[char] + 1
  char_map[char] = right
  max_len = max(max_len, right - left + 1)
 return max_len
```
