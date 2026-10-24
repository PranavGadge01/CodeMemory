# Attempts History: Roman to Integer

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:45 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `46.2 MB`
- **Timestamp**: `2026-03-28 13:28:12 UTC`

```java
class Solution {
    private int getVal(char ch) {
        switch(ch) {
            case 'I': return 1;
            case 'V': return 5;
            case 'X': return 10;
            case 'L': return 50;
            case 'C': return 100;
            case 'D': return 500;
            case 'M': return 1000;
            default: return 0;
        }
    }

    public int romanToInt(String s) {
        int total = 0;
        int n = s.length();

        for (int i = 0; i < n; i++) {
            int curr = getVal(s.charAt(i));

            if (i < n - 1 && curr < getVal(s.charAt(i + 1))) {
                total -= curr;
            } else {
                total += curr;
            }
        }

        return total;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:46 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `46.2 MB`
- **Timestamp**: `2026-03-28 13:24:51 UTC`

```java
import java.util.*;

class Solution {
    private static int getSymbolVal(char symbol){
        switch(symbol){
            case 'I': return 1;
            case 'V': return 5;
            case 'X': return 10;
            case 'L': return 50;
            case 'C': return 100;
            case 'D': return 500;
            case 'M': return 1000;
            default : return 0;
        }
    }

    public int romanToInt(String s) {
        char prevSymbol = '0';
        int intValue = 0;

        for(char symbol: s.toCharArray()){
            int val = getSymbolVal(symbol);
            int prevVal = getSymbolVal(prevSymbol);

            if(val > prevVal){
                intValue = intValue - prevVal;
                val = val - prevVal;
            }

            intValue = intValue + val;
            prevSymbol = symbol;
        }

        return intValue;
    }
}
```
