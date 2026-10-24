# Solution for Two Sum
# Status: Accepted
# Language: python

def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen: return [seen[target - num], i]
        seen[num] = i
    return []