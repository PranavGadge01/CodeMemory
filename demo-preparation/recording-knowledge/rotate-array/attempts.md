# Attempts History: Rotate Array

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:12 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `61.0 MB`
- **Timestamp**: `2026-03-23 17:11:40 UTC`

```java
class Solution {
    public void rotate(int[] nums, int k) {
        int n = nums.length;
        k = k % n;

        reverse(nums, 0, n - 1);
        reverse(nums, 0, k - 1);
        reverse(nums, k, n - 1);
    }

    private void reverse(int[] nums, int left, int right) {
        while(left < right){
            int temp = nums[left];
            nums[left] = nums[right];
            nums[right] = temp;
            left++;
            right--;
        }
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:13 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `1.0 ms` | **Memory**: `63.1 MB`
- **Timestamp**: `2026-03-23 17:11:03 UTC`

```java
class Solution {
    public void rotate(int[] nums, int k) {
        int n = nums.length;
        k = k % n;

        int temp[] = new int[k];

        // copy rotated part
        for(int i = (n - k); i < n; i++){
            temp[i - (n - k)] = nums[i];
        }

        // shift non-rotated part
        for(int i = (n - k - 1); i >= 0; i--){
            nums[i + k] = nums[i];
        }

        // put rotated part in array
        for(int i = 0; i < k; i++){
            nums[i] = temp[i];
        }
    }
}
```
