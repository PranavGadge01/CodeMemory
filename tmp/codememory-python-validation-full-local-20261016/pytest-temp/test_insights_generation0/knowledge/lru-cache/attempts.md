# Attempts History: LRU Cache

## Attempt 1: Doubly Linked List + Hash Map
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:36 UTC`
- **Reasoning**: Use hash map for O(1) key-to-node lookup and DLL for O(1) eviction/insertion.
- **Time Complexity**: `O(1)`
- **Space Complexity**: `O(capacity)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:36 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `120.0 ms` | **Memory**: `75.4 MB`
- **Timestamp**: `2026-10-15 19:06:36 UTC`

```py
class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = {}

```
