# Attempts History: Zigzag Conversion

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:50 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `4.0 ms` | **Memory**: `46.5 MB`
- **Timestamp**: `2026-03-27 18:59:19 UTC`

```java
class Solution {
    public String convert(String s, int numRows) {
        if (numRows == 1 || s.length() <= numRows) return s;

        StringBuilder[] rows = new StringBuilder[numRows];
        for (int i = 0; i < numRows; i++) {
            rows[i] = new StringBuilder();
        }

        int currRow = 0;
        boolean goingDown = false;

        for (char c : s.toCharArray()) {
            rows[currRow].append(c);

            if (currRow == 0 || currRow == numRows - 1) {
                goingDown = !goingDown;
            }

            currRow += goingDown ? 1 : -1;
        }

        StringBuilder result = new StringBuilder();
        for (StringBuilder row : rows) {
            result.append(row);
        }

        return result.toString();
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Runtime Error`
- **Date**: `2026-10-19 12:56:50 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Runtime Error` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-27 18:55:52 UTC`

```java

```
