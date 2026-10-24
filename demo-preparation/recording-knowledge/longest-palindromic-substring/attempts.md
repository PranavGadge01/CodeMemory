# Attempts History: Longest Palindromic Substring

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:56 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `14.0 ms` | **Memory**: `43.8 MB`
- **Timestamp**: `2026-03-26 07:30:31 UTC`

```java
class Solution {
    public String longestPalindrome(String s) {
        if(s.length() < 1) return "";

        int start = 0, end = 0;

        for(int i = 0; i < s.length(); i++){
            int len1 = expand(s, i, i);     // odd
            int len2 = expand(s, i, i+1);   // even

            int len = Math.max(len1, len2);

            if(len > end - start){
                start = i - (len - 1) / 2;
                end = i + len / 2;
            }
        }

        return s.substring(start, end + 1);
    }

    private int expand(String s, int left, int right){
        while(left >= 0 && right < s.length() && s.charAt(left) == s.charAt(right)){
            left--;
            right++;
        }
        return right - left - 1;
    }
}
```
