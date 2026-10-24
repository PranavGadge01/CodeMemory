# Solution for LRU Cache
# Status: Accepted
# Language: python

class LRUCache:
    def __init__(self, capacity: int):
        self.cap = capacity
        self.cache = {}
