# Solution for Two Sum
# Status: Accepted
# Language: python

def twoSum(nums, target):
 hashmap = {}
 for i, n in enumerate(nums):
  if target - n in hashmap: return [hashmap[target - n], i]
  hashmap[n] = i