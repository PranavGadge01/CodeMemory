# Attempts History: Word Search II

## Attempt 1: Trie-based Backtracking DFS
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Construct Trie of words and prune invalid search branches early during board DFS.
- **Time Complexity**: `O(M * N * 4^L)`
- **Space Complexity**: `O(SUM(len(word)))`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `1200.0 ms` | **Memory**: `35.0 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False

```
