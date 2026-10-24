# Solution for Dp One
# Status: Wrong Answer
# Language: python

total = 0
for i in range(len(nums)):
    for j in range(len(nums)):
        if nums[i] + nums[j] == target:
            total += 1
return total