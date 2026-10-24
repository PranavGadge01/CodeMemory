# Solution for Merge Intervals
# Status: Accepted
# Language: Python

class Solution:
    def merge(self, intervals):
        intervals.sort()
        res = [intervals[0]]
        for s, e in intervals[1:]:
            if s <= res[-1][1]:
                res[-1][1] = max(res[-1][1], e)
            else:
                res.append([s, e])
        return res