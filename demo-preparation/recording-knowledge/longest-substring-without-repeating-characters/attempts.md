# Attempts History: Longest Substring Without Repeating Characters

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:46 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `5.0 ms` | **Memory**: `45.3 MB`
- **Timestamp**: `2026-03-20 07:02:33 UTC`

```java
import java.util.HashMap;

class Solution {
    public int lengthOfLongestSubstring(String s) {
        HashMap<Character, Integer> hash = new HashMap<Character, Integer>();
        int left = 0, right = 0, maxLength = 0;
        int n = s.length();
        while(right < n){
            char ch = s.charAt(right);
            if(hash.containsKey(ch)) {
                left = Math.max(left, hash.get(ch) + 1);
            }

            int len = right - left + 1;
            maxLength = Math.max(len, maxLength);

            hash.put(ch, right);
            right++;
        }

        return maxLength;

    }
}
```
