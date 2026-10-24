# Solution for W Two
# Status: Wrong Answer
# Language: python

nums.sort()
left, right = 0, len(nums) - 1
while left < right:
    total = nums[left] + nums[right]
    if total == target:
        return [left, right]
    left += 1
return []