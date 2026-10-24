# Solution for Longest Substring Without Repeating Characters
# Status: Accepted
# Language: python

def lengthOfLongestSubstring(s):
 char_map = {}
 left = max_len = 0
 for right, char in enumerate(s):
  if char in char_map and char_map[char] >= left: left = char_map[char] + 1
  char_map[char] = right
  max_len = max(max_len, right - left + 1)
 return max_len