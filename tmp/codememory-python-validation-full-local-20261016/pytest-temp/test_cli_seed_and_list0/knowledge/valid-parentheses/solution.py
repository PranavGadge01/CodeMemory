# Solution for Valid Parentheses
# Status: Accepted
# Language: python

def isValid(s: str) -> bool:
    stack = []
    mp = {')': '(', '}': '{', ']': '['}
    for char in s:
        if char in mp:
            top = stack.pop() if stack else '#'
            if mp[char] != top: return False
        else: stack.append(char)
    return not stack