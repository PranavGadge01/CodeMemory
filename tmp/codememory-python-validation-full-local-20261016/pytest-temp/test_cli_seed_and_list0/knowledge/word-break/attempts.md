# Attempts History: Word Break

## Attempt 1: 1D DP Array
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:30 UTC`
- **Reasoning**: dp[i] represents whether s[:i] can be segmented into words in wordDict.
- **Time Complexity**: `O(N^2 * M)`
- **Space Complexity**: `O(N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:30 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `40.0 ms` | **Memory**: `16.2 MB`
- **Timestamp**: `2026-10-15 19:06:30 UTC`

```py
def wordBreak(s: str, wordDict: list[str]) -> bool:
    words = set(wordDict)
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in words:
                dp[i] = True
                break
    return dp[len(s)]
```
