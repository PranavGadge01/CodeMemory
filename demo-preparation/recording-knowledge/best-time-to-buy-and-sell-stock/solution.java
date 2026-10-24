# Solution for Best Time to Buy and Sell Stock
# Status: Accepted
# Language: Java

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