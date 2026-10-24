# Attempts History: Longest Common Prefix

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:52 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `43.1 MB`
- **Timestamp**: `2026-03-27 18:01:44 UTC`

```java
class Solution {
    public String longestCommonPrefix(String[] strs) {
        if(strs.length == 0) return "";

        for(int i = 0; i < strs[0].length(); i++){
            char ch = strs[0].charAt(i);

            for(int j = 1; j < strs.length; j++){
                if(i == strs[j].length() || strs[j].charAt(i) != ch){
                    return strs[0].substring(0, i);
                }
            }
        }

        return strs[0];
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:53 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `43.5 MB`
- **Timestamp**: `2026-03-27 17:56:27 UTC`

```java
class Solution {
    public String longestCommonPrefix(String[] strs) {
        if(strs.length < 1) return "";

        String lcp = "";
        int len = strs[0].length();

        for(int i = 0; i < len; i++){
            String subStr =  strs[0].substring(0, len - i);
            boolean isValid = true;

            for(int j = 1; j <strs.length; j++){
                if(!strs[j].startsWith(subStr)){
                    isValid = false;
                    break;
                }
            }

            if(isValid && subStr.length() > lcp.length()){
                lcp = subStr;
            }
        }


        return lcp;
    }
}
```
