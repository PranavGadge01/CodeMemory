# Solution for Valid Parentheses
# Status: Accepted
# Language: Python

class Solution:\n    def isValid(self, s: str) -> bool:\n        st = []\n        m = {')': '(', '}': '{', ']': '['}\n        for c in s:\n            if c in m:\n                if not st or st.pop() != m[c]: return False\n            else: st.append(c)\n        return not st