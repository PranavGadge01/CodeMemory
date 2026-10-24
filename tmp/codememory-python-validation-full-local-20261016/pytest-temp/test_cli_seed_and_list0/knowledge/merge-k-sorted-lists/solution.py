# Solution for Merge k Sorted Lists
# Status: Accepted
# Language: python

def mergeKLists(lists):
    if not lists: return None
    while len(lists) > 1:
        merged = []
        for i in range(0, len(lists), 2):
            l1 = lists[i]
            l2 = lists[i+1] if (i+1) < len(lists) else None
            merged.append(mergeTwo(l1, l2))
        lists = merged
    return lists[0]