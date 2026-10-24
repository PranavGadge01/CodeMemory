# Attempts History: Frequency of the Most Frequent Element

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:15 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `34.0 ms` | **Memory**: `94.6 MB`
- **Timestamp**: `2026-03-22 14:44:09 UTC`

```java
import java.util.Arrays;

class Solution {
    public int maxFrequency(int[] nums, int k) {
        Arrays.sort(nums);

        
        /* left and right are sliding window pointers only moves forward so at max each element is visited twice only(that's why time complexity is O(n))
        */
        int left = 0;
        long sum = 0;
        int maxFreq = 0;

        for(int right = 0; right < nums.length; right++){
            sum += nums[right];

            // Check if window is invalid
            while((long)nums[right] * (right - left + 1) - sum > k){
                sum -= nums[left];
                left++;
            }

            maxFreq = Math.max(maxFreq, right - left + 1);
        }

        return maxFreq;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:16 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `34.0 ms` | **Memory**: `95.0 MB`
- **Timestamp**: `2026-03-22 14:43:01 UTC`

```java
class Solution {
    public int maxFrequency(int[] nums, int k) {
        Arrays.sort(nums);

        /* left and right are sliding window pointers only moves forward so at max each element is visited twice only(that's why time complexity is O(n))
        */
        int left = 0, right = 0;
        int maxFreq = 0;
        long sum = 0;


        while(right < nums.length){
            sum += nums[right];

            // Check if window is invalid
            while((long)nums[right] * (right - left + 1) > sum + k){
                sum -= nums[left];
                left++;
            }

            maxFreq = Math.max(maxFreq, (right - left + 1));

            right++;
        }

        return maxFreq;
    }
}
```

## Attempt 3: Attempt 3
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:16 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `34.0 ms` | **Memory**: `95.0 MB`
- **Timestamp**: `2026-03-22 14:40:11 UTC`

```java
class Solution {
    public int maxFrequency(int[] nums, int k) {
        Arrays.sort(nums);
        int left = 0, right = 0;
        long res = 0, total = 0;

        while (right < nums.length) {
            total += nums[right];

            while (nums[right] * (right - left + 1L) > total + k) {
                total -= nums[left];
                left += 1;
            }

            res = Math.max(res, right - left + 1L);
            right += 1;
        }

        return (int) res;        
    }
}
```

## Attempt 4: Attempt 4
- **Status**: `Wrong Answer`
- **Date**: `2026-10-19 12:57:17 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-22 14:37:02 UTC`

```java

```

#### Submission 2 (Java)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2026-03-22 14:38:45 UTC`

```java

```
