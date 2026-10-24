# Attempts History: Length of Last Word

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:28 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `N/A` | **Memory**: `43.2 MB`
- **Timestamp**: `2026-04-03 23:46:34 UTC`

```java
class Solution {
    public int lengthOfLastWord(String s) {
        int i = s.length() - 1;

        while (i >= 0 && s.charAt(i) == ' ') {
            i--;
        }

        int length = 0;
        while (i >= 0 && s.charAt(i) != ' ') {
            length++;
            i--;
        }

        return length;
    }
}
```
