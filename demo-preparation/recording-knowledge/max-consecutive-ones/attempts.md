# Attempts History: Max Consecutive Ones

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:02 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `52.1 MB`
- **Timestamp**: `2026-03-24 17:47:12 UTC`

```java
class Solution {
    public int findMaxConsecutiveOnes(int[] nums) {
        int maxOnes = 0, tempOnes = 0;
        int n = nums.length;

        for(int i = 0; i < n; i++){
            if(nums[i] == 1) tempOnes++;
            else tempOnes = 0;

            maxOnes = Math.max(maxOnes, tempOnes);
        }

        return maxOnes;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:02 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `52.7 MB`
- **Timestamp**: `2026-03-24 17:45:21 UTC`

```java
class Solution {
    public int findMaxConsecutiveOnes(int[] nums) {
        int maxOnes = 0, tempOnes = 0;
        int n = nums.length;

        for(int i = 0; i < n; i++){
            if(nums[i] == 1) tempOnes++;
            else tempOnes = 0;

            maxOnes = Math.max(maxOnes, tempOnes);
        }

        return maxOnes;
    }
}
```
