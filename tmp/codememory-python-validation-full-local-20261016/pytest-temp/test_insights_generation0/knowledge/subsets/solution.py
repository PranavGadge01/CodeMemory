# Solution for Subsets
# Status: Accepted
# Language: python

def subsets(nums: list[int]) -> list[list[int]]:
    res = []
    def backtrack(idx, path):
        if idx == len(nums):
            res.append(path[:]); return
        backtrack(idx + 1, path + [nums[idx]])
        backtrack(idx + 1, path)
    backtrack(0, [])
    return res