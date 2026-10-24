# Solution for Swap Nodes in Pairs
# Status: Accepted
# Language: Java

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