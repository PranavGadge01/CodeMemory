# Solution for Word Search II
# Status: Accepted
# Language: python

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False
