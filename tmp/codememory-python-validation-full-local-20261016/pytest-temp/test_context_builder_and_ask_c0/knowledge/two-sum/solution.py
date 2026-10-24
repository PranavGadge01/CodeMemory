# Solution for Two Sum
# Status: Accepted
# Language: python

def twoSum(nums, target):
 seen = {}
 for i, n in enumerate(nums):
  if target - n in seen: return [seen[target - n], i]
  seen[n] = i