# Attempts History: Valid Anagram

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:24 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `6.0 ms` | **Memory**: `44.2 MB`
- **Timestamp**: `2026-03-21 14:15:17 UTC`

```java
class Solution {
    public boolean isAnagram(String s, String t) {
        if(s.length() != t.length()) return false;

        int[] counts = new int[26];

        for(int i = 0; i < s.length(); i++){
            counts[s.charAt(i) - 'a']++;
            counts[t.charAt(i) - 'a']--;
        }

        for(int c : counts){
            if(c != 0) return false;
        }

        return true;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:25 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `6.0 ms` | **Memory**: `44.4 MB`
- **Timestamp**: `2026-03-21 14:14:54 UTC`

```java
class Solution {
    public boolean isAnagram(String s, String t) {
        if(s.length() != t.length()) return false;

        int[] counts = new int[26];

        for(int i = 0; i < s.length(); i++){
            counts[s.charAt(i) - 'a']++;
            counts[t.charAt(i) - 'a']--;
        }

        for(int i = 0; i < 26; i++){
            if(counts[i] != 0) return false;
        }

        return true;
    }
}
```

## Attempt 3: Attempt 3
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:25 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `6.0 ms` | **Memory**: `44.4 MB`
- **Timestamp**: `2026-03-21 14:10:25 UTC`

```java
class Solution {
    public boolean isAnagram(String s, String t) {
        if(s.length() != t.length()) return false;

        int[] counts = new int[26];

        for(int i = 0; i < s.length(); i++){
            counts[s.charAt(i) - 'a']++;
            counts[t.charAt(i) - 'a']--;
        }

        for(int c : counts){
            if(c != 0) return false;
        }

        return true;
    }
}
```
