# Solution for Valid Parentheses
# Status: Accepted
# Language: Java

import java.util.Deque;
import java.util.ArrayDeque;

class Solution {
    public boolean isValid(String s) {
        Deque<Character> stack = new ArrayDeque<>();

        for(char ch : s.toCharArray()){
            if(ch == '(') stack.push(')');
            else if(ch == '[') stack.push(']');
            else if(ch == '{') stack.push('}');
            else {
                if(stack.isEmpty() || stack.pop() != ch){
                    return false;
                }
            }
        }

        return stack.isEmpty();
    }
}