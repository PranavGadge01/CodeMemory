# Solution for Valid Palindrome
# Status: Accepted
# Language: Java

class Solution {
    public boolean isPalindrome(String s) {
        int left = 0, right = s.length() - 1;

        while(left < right){
            char ch1 = s.charAt(left);
            char ch2 = s.charAt(right);

            if(!Character.isLetterOrDigit(ch1)){
                left++;
                continue;
            }
            if(!Character.isLetterOrDigit(ch2)){
                right--;
                continue;
            }

            if(Character.toLowerCase(ch1) != Character.toLowerCase(ch2)){
                return false;
            }

            left++;
            right--;
        }

        return true;
    }
}