# Attempts History: Clone Graph

## Attempt 1: DFS with Hash Map Tracker
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Map original node to cloned node to handle cycles cleanly during DFS.
- **Time Complexity**: `O(V + E)`
- **Space Complexity**: `O(V)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `42.0 ms` | **Memory**: `16.7 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
def cloneGraph(node):
    if not node: return None
    old_to_new = {}
    def dfs(n):
        if n in old_to_new: return old_to_new[n]
        copy = Node(n.val)
        old_to_new[n] = copy
        for nei in n.neighbors:
            copy.neighbors.append(dfs(nei))
        return copy
    return dfs(node)
```
