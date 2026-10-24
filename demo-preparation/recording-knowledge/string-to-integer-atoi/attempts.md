# Attempts History: String to Integer (atoi)

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:47 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `43.7 MB`
- **Timestamp**: `2026-03-27 19:42:35 UTC`

```java
class Solution {
    public int myAtoi(String s) {
        int n = s.length();
        if(n == 0) return 0;

        int i = 0;

        while (i < n && s.charAt(i) == ' ') i++;

        int sign = 1;
        if (i < n && (s.charAt(i) == '+' || s.charAt(i) == '-')) {
            if (s.charAt(i) == '-') sign = -1;
            i++;
        }

        int result = 0;
        while (i < n && Character.isDigit(s.charAt(i))) {
            int digit = s.charAt(i) - '0';

            if (result > (Integer.MAX_VALUE - digit) / 10) {
                return sign == 1 ? Integer.MAX_VALUE : Integer.MIN_VALUE;
            }

            result = result * 10 + digit;
            i++;
        }

        return result * sign;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:48 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `43.9 MB`
- **Timestamp**: `2026-03-27 19:40:46 UTC`

```java
class Solution {
    public int myAtoi(String s) {
        int n = s.length();
        int i = 0;

        while (i < n && s.charAt(i) == ' ') i++;

        int sign = 1;
        if (i < n && (s.charAt(i) == '+' || s.charAt(i) == '-')) {
            if (s.charAt(i) == '-') sign = -1;
            i++;
        }

        int result = 0;
        while (i < n && Character.isDigit(s.charAt(i))) {
            int digit = s.charAt(i) - '0';

            if (result > (Integer.MAX_VALUE - digit) / 10) {
                return sign == 1 ? Integer.MAX_VALUE : Integer.MIN_VALUE;
            }

            result = result * 10 + digit;
            i++;
        }

        return result * sign;
    }
}
```

## Attempt 3: Attempt 3
- **Status**: `Wrong Answer`
- **Date**: `2026-10-19 12:56:48 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-27 19:29:33 UTC`

```java

```

#### Submission 2 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-27 19:31:20 UTC`

```java

```

#### Submission 3 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-27 19:31:43 UTC`

```java

```

#### Submission 4 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-27 19:37:05 UTC`

```java

```
