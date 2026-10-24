# Attempts History: Number of Islands

## Attempt 1: Grid DFS Traversal
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Traverse 2D matrix; when land '1' encountered, increment island count and DFS sink all connected '1's.
- **Time Complexity**: `O(M * N)`
- **Space Complexity**: `O(M * N)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `210.0 ms` | **Memory**: `32.1 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def numIslands(grid: list[list[str]]) -> int:
    if not grid: return 0
    rows, cols = len(grid), len(grid[0])
    count = 0
    def dfs(r, c):
        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] != '1': return
        grid[r][c] = '0'
        dfs(r+1, c); dfs(r-1, c); dfs(r, c+1); dfs(r, c-1)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1
                dfs(r, c)
    return count
```
