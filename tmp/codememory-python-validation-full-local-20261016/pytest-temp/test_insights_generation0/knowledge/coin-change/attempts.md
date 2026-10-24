# Attempts History: Coin Change

## Attempt 1: Bottom-Up DP
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:36 UTC`
- **Reasoning**: dp[i] stores min coins to form amount i: dp[i] = min(dp[i], dp[i - coin] + 1).
- **Time Complexity**: `O(amount * len(coins))`
- **Space Complexity**: `O(amount)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `650.0 ms` | **Memory**: `16.8 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
def coinChange(coins: list[int], amount: int) -> int:
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for i in range(coin, amount + 1):
            dp[i] = min(dp[i], dp[i - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1
```
