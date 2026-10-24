# Solution for Max Consecutive Ones
# Status: Accepted
# Language: Java

class Solution {
    public int findMaxConsecutiveOnes(int[] nums) {
        int maxOnes = 0, tempOnes = 0;
        int n = nums.length;

        for(int i = 0; i < n; i++){
            if(nums[i] == 1) tempOnes++;
            else tempOnes = 0;

            maxOnes = Math.max(maxOnes, tempOnes);
        }

        return maxOnes;
    }
}