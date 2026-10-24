# Solution for P 6
# Status: Accepted
# Language: python

seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        return [seen[target - n], i]
    seen[n] = i
return []