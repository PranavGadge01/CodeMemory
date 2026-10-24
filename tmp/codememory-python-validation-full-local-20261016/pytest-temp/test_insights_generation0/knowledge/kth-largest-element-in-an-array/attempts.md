# Attempts History: Kth Largest Element in an Array

## Attempt 1: Min Heap of Size K
- **Status**: `Unknown`
- **Date**: `2026-10-15 19:06:37 UTC`
- **Reasoning**: Maintain min heap of size k; top element will be kth largest.
- **Time Complexity**: `O(N log K)`
- **Space Complexity**: `O(K)`

### Submissions
*No code submission recorded for this attempt.*

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-15 19:06:37 UTC`

### Submissions
#### Submission 1 (python)
- **Result**: `Accepted` | **Runtime**: `450.0 ms` | **Memory**: `27.0 MB`
- **Timestamp**: `2026-10-15 19:06:37 UTC`

```py
import heapq
def findKthLargest(nums: list[int], k: int) -> int:
    heap = []
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
```
