# Attempts History: Course Schedule

## Attempt 1: Kahn's Algorithm (Topological Sort BFS)
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Track in-degrees of nodes; process 0 in-degree nodes via BFS queue.
- **Time Complexity**: `O(V + E)`
- **Space Complexity**: `O(V + E)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `85.0 ms` | **Memory**: `17.5 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
from collections import deque
def canFinish(numCourses: int, prerequisites: list[list[int]]) -> bool:
    adj = [[] for _ in range(numCourses)]
    indegree = [0] * numCourses
    for crs, pre in prerequisites:
        adj[pre].append(crs)
        indegree[crs] += 1
    q = deque([i for i in range(numCourses) if indegree[i] == 0])
    visited = 0
    while q:
        node = q.popleft()
        visited += 1
        for nxt in adj[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0: q.append(nxt)
    return visited == numCourses
```
