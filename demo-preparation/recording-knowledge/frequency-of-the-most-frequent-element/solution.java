# Solution for Frequency of the Most Frequent Element
# Status: Accepted
# Language: Java

import java.util.Arrays;

class Solution {
    public int maxFrequency(int[] nums, int k) {
        Arrays.sort(nums);

        
        /* left and right are sliding window pointers only moves forward so at max each element is visited twice only(that's why time complexity is O(n))
        */
        int left = 0;
        long sum = 0;
        int maxFreq = 0;

        for(int right = 0; right < nums.length; right++){
            sum += nums[right];

            // Check if window is invalid
            while((long)nums[right] * (right - left + 1) - sum > k){
                sum -= nums[left];
                left++;
            }

            maxFreq = Math.max(maxFreq, right - left + 1);
        }

        return maxFreq;
    }
}