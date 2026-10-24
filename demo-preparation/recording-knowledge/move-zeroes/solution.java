# Solution for Move Zeroes
# Status: Accepted
# Language: Java

class Solution {
    public void moveZeroes(int[] nums) {
        int insertPos = 0;

        for(int num : nums){
            if(num != 0){
                nums[insertPos++] = num;
            }
        }

        while(insertPos < nums.length){
            nums[insertPos++] = 0;
        }
    }
}