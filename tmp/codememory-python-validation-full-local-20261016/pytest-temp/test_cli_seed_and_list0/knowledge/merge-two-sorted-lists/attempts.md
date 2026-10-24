# Attempts History: Merge Two Sorted Lists

## Attempt 1: Dummy Node Iterative Merge
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:29 UTC`
- **Reasoning**: Compare heads of list1 and list2, appending smaller node to dummy tail.
- **Time Complexity**: `O(N + M)`
- **Space Complexity**: `O(1)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:29 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `38.0 ms` | **Memory**: `15.0 MB`
- **Timestamp**: `2026-10-15 19:06:29 UTC`

```py
def mergeTwoLists(l1, l2):
    dummy = curr = ListNode(0)
    while l1 and l2:
        if l1.val < l2.val:
            curr.next, l1 = l1, l1.next
        else:
            curr.next, l2 = l2, l2.next
        curr = curr.next
    curr.next = l1 or l2
    return dummy.next
```
