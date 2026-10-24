# Solution for Generate Parentheses
# Status: Accepted
# Language: Java

class Solution {
    private void build(int o, int c, List<String> res, String pattern) {
        if (o == 0 && c == 0) {
            res.add(pattern);
            return;
        }

        if (o > 0) {
            build(o - 1, c, res, pattern + "(");
        }

        if (c > o) {
            build(o, c - 1, res, pattern + ")");
        }
    }

    public List<String> generateParenthesis(int n) {
        List<String> res = new ArrayList<>();
        build(n, n, res, "");
        return res;
    }
}