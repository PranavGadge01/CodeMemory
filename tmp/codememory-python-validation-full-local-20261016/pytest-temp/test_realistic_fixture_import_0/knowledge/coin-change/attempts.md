# Attempts History: Coin Change

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-18 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `1120.0 ms` | **Memory**: `14.6 MB`
- **Timestamp**: `2024-01-18 09:00:00 UTC`

```py
class Solution:
    def coinChange(self, coins, amount):
        dp = [float('inf')] * (amount + 1)
        dp[0] = 0
        for i in range(1, amount + 1):
            for c in coins:
                if c <= i:
                    dp[i] = min(dp[i], dp[i - c] + 1)
        return dp[amount] if dp[amount] != float('inf') else -1
```
