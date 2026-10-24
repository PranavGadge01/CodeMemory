# Solution for Binary Tree Level Order Traversal
# Status: Accepted
# Language: python

from collections import deque
def levelOrder(root):
    if not root: return []
    q = deque([root]); res = []
    while q:
        level = []
        for _ in range(len(q)):
            n = q.popleft(); level.append(n.val)
            if n.left: q.append(n.left)
            if n.right: q.append(n.right)
        res.append(level)
    return res