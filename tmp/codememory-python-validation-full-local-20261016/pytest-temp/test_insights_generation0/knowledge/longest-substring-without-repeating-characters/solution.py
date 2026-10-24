# Solution for Longest Substring Without Repeating Characters
# Status: Accepted
# Language: python

def lengthOfLongestSubstring(s: str) -> int:
    seen = {}
    left = max_len = 0
    for right, char in enumerate(s):
        if char in seen and seen[char] >= left:
            left = seen[char] + 1
        seen[char] = right
        max_len = max(max_len, right - left + 1)
    return max_len