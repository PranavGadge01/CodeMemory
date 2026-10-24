# Solution for P 0
# Status: Wrong Answer
# Language: python

seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []