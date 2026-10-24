# Solution for Subsets
# Status: Accepted
# Language: python

def subsets(nums):
    res = [[]]
    for n in nums:
        res += [r + [n] for r in res]
    return res