# Attempts History: Best Time to Buy and Sell Stock

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-11 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `58.0 ms` | **Memory**: `23.1 MB`
- **Timestamp**: `2024-01-11 09:00:00 UTC`

```py
class Solution:
    def maxProfit(self, prices):
        min_price = float('inf')
        max_profit = 0
        for p in prices:
            min_price = min(min_price, p)
            max_profit = max(max_profit, p - min_price)
        return max_profit
```
