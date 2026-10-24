# Solution for Best Time to Buy and Sell Stock
# Status: Accepted
# Language: Python

class Solution:
    def maxProfit(self, prices):
        min_price = float('inf')
        max_profit = 0
        for p in prices:
            min_price = min(min_price, p)
            max_profit = max(max_profit, p - min_price)
        return max_profit