# Solution for Container With Most Water
# Status: Accepted
# Language: python

def maxArea(height: list[int]) -> int:
    l, r = 0, len(height) - 1
    ans = 0
    while l < r:
        w = r - l
        h = min(height[l], height[r])
        ans = max(ans, w * h)
        if height[l] < height[r]: l += 1
        else: r -= 1
    return ans