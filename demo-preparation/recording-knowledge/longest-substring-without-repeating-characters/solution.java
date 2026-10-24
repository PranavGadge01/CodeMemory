# Solution for Longest Substring Without Repeating Characters
# Status: Accepted
# Language: Java

import java.util.HashMap;

class Solution {
    public int lengthOfLongestSubstring(String s) {
        HashMap<Character, Integer> hash = new HashMap<Character, Integer>();
        int left = 0, right = 0, maxLength = 0;
        int n = s.length();
        while(right < n){
            char ch = s.charAt(right);
            if(hash.containsKey(ch)) {
                left = Math.max(left, hash.get(ch) + 1);
            }

            int len = right - left + 1;
            maxLength = Math.max(len, maxLength);

            hash.put(ch, right);
            right++;
        }

        return maxLength;

    }
}