# Attempts History: Valid Palindrome

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:31 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `44.4 MB`
- **Timestamp**: `2026-03-21 13:45:33 UTC`

```java
class Solution {
    public boolean isPalindrome(String s) {
        int left = 0, right = s.length() - 1;

        while(left < right){
            char ch1 = s.charAt(left);
            char ch2 = s.charAt(right);

            if(!Character.isLetterOrDigit(ch1)){
                left++;
                continue;
            }
            if(!Character.isLetterOrDigit(ch2)){
                right--;
                continue;
            }

            if(Character.toLowerCase(ch1) != Character.toLowerCase(ch2)){
                return false;
            }

            left++;
            right--;
        }

        return true;
    }
}
```
