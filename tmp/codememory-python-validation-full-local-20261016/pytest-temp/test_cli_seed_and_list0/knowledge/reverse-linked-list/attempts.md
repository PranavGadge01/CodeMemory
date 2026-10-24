# Attempts History: Reverse Linked List

## Attempt 1: Iterative Three Pointers
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Maintain prev, curr, and nxt pointers to re-link nodes in place.
- **Time Complexity**: `O(N)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `32.0 ms` | **Memory**: `15.2 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def reverseList(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
```
