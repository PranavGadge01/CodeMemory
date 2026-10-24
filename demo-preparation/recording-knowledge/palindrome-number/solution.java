# Solution for Palindrome Number
# Status: Accepted
# Language: Java

class Solution {
    public boolean isPalindrome(int x) {
        // Negative numbers OR numbers ending with 0 (except 0)
        if(x < 0 || (x % 10 == 0 && x != 0)) {
            return false;
        }

        int rev = 0;

        while(x > rev) {
            int digit = x % 10;
            rev = rev * 10 + digit;
            x /= 10;
        }

        // For even digits: x == rev
        // For odd digits: x == rev/10
        return (x == rev) || (x == rev / 10);
    }
}