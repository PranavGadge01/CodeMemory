# Solution for Letter Combinations of a Phone Number
# Status: Accepted
# Language: Java

class Solution {
    public List<String> letterCombinations(String digits) {
        List<String> result = new ArrayList<>();
        
        if (digits.length() == 0) return result;

        String[] map = {
            "",     // 0
            "",     // 1
            "abc",  // 2
            "def",  // 3
            "ghi",  // 4
            "jkl",  // 5
            "mno",  // 6
            "pqrs", // 7
            "tuv",  // 8
            "wxyz"  // 9
        };

        backtrack(result, digits, map, 0, new StringBuilder());
        return result;
    }

    private void backtrack(List<String> result, String digits, String[] map, int index, StringBuilder current) {
        
        // Base case
        if (index == digits.length()) {
            result.add(current.toString());
            return;
        }

        String letters = map[digits.charAt(index) - '0'];

        for (char ch : letters.toCharArray()) {
            current.append(ch);              // choose
            backtrack(result, digits, map, index + 1, current); // explore
            current.deleteCharAt(current.length() - 1); // un-choose
        }
    }
}