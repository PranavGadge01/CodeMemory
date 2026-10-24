# Attempts History: Remove Duplicates from Sorted Array

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:43 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `46.8 MB`
- **Timestamp**: `2026-03-20 15:36:24 UTC`

```java
class Solution {
    public int removeDuplicates(int[] nums) {
        if(nums.length == 0) return 0;

        int k = 1;

        for(int i = 1; i < nums.length; i++){
            if(nums[i] != nums[i - 1]) {
                nums[k] = nums[i];
                k++;
            }
        }

        return k;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:44 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `46.5 MB`
- **Timestamp**: `2026-03-20 15:36:10 UTC`

```java
class Solution {
    public int removeDuplicates(int[] nums) {
        if(nums.length == 0) return 0;

        int k = 1;

        for(int i = 1; i < nums.length; i++){
            if(nums[i] != nums[i - 1]) {
                nums[k] = nums[i];
                k++;
            }
        }

        return k;
    }
}
```
