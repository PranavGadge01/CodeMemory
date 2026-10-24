# Attempts History: Binary Tree Level Order Traversal

## Attempt 1: BFS Queue Traversal
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Use deque to traverse tree level by level.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `42.0 ms` | **Memory**: `17.0 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
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
```
