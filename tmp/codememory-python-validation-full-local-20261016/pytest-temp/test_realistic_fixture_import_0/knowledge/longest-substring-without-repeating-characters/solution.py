# Solution for Longest Substring Without Repeating Characters
# Status: Accepted
# Language: Python

class Solution:
    def lengthOfLongestSubstring(self, s):
        seen = set()
        left = 0
        max_len = 0
        for right, c in enumerate(s):
            while c in seen:
                seen.remove(s[left])
                left += 1
            seen.add(c)
            max_len = max(max_len, right - left + 1)
        return max_len