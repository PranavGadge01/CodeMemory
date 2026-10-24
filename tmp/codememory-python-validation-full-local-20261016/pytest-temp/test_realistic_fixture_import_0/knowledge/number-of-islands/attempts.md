# Attempts History: Number of Islands

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2024-01-20 09:00:00 UTC`

### Submissions
#### Submission 1 (Python)
- **Result**: `Accepted` | **Runtime**: `189.0 ms` | **Memory**: `17.5 MB`
- **Timestamp**: `2024-01-20 09:00:00 UTC`

```py
class Solution:
    def numIslands(self, grid):
        if not grid: return 0
        count = 0
        def dfs(r, c):
            if r < 0 or c < 0 or r >= len(grid) or c >= len(grid[0]) or grid[r][c] == '0': return
            grid[r][c] = '0'
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]: dfs(r+dr, c+dc)
        for r in range(len(grid)):
            for c in range(len(grid[0])):
                if grid[r][c] == '1':
                    dfs(r, c); count += 1
        return count
```
