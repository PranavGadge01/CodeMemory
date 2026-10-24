# Attempts History: Swap Nodes in Pairs

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:12 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `42.7 MB`
- **Timestamp**: `2026-09-19 10:09:26 UTC`

```java
/**
 * Definition for singly-linked list.
 * public class ListNode {
 *     int val;
 *     ListNode next;
 *     ListNode() {}
 *     ListNode(int val) { this.val = val; }
 *     ListNode(int val, ListNode next) { this.val = val; this.next = next; }
 * }
 */
class Solution {
    public ListNode swapPairs(ListNode head) {
        if(head == null || head.next == null){
            return head;
        }

        ListNode temp = head;
        head = temp.next;
        ListNode prev = null;
        while(temp != null && temp.next != null){
            ListNode next = temp.next;
            temp.next = next.next;
            next.next = temp;
            if(prev != null){
                prev.next = next;
            }
            prev = temp;
            temp = temp.next;
        }

        return head;
    }
}
```
