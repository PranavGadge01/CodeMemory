# Attempts History: Best Time to Buy and Sell Stock

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:32 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `94.5 MB`
- **Timestamp**: `2026-03-21 07:00:30 UTC`

```java
class Solution {
    public int maxProfit(int[] prices) {
        int maxProfit = 0, i = 0, j = 0;

        while(j < prices.length){
            
            if(prices[i] > prices[j]){
                i = j;
            }else{
                int profit = prices[j] - prices[i];
                if(profit > maxProfit){
                    maxProfit = profit;
                }
            }

            j++;
        }

        return maxProfit;
        
    }
}
```
