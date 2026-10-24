# Attempts History: Majority Element

## Attempt 1: Attempt 1
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:56:58 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `3.0 ms` | **Memory**: `55.6 MB`
- **Timestamp**: `2026-03-25 17:40:39 UTC`

```java
class Solution {
    public int majorityElement(int[] nums) {
        int count = 0;
        int candidate = 0;

        for(int num : nums){
            if(count == 0){
                candidate = num;
            }

            if(num == candidate){
                count++;
            } else {
                count--;
            }
        }

        return candidate;
    }
}
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:00 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `16.0 ms` | **Memory**: `52.4 MB`
- **Timestamp**: `2026-03-25 17:32:46 UTC`

```java
import java.util.HashMap;

class Solution {
    public int majorityElement(int[] nums) {
        int nBy2 = nums.length / 2;
        int majority = 0, res = 1;

        HashMap<Integer, Integer> map = new HashMap<Integer, Integer>();
        
        for(int i = 0; i < nums.length; i++){
            int freq = 0;
            if(map.containsKey(nums[i])){
                freq =  map.get(nums[i]) + 1;
                map.replace(nums[i], freq);
            }else{
                freq = 1;
                map.put(nums[i], freq);
            }

            if(majority < freq){
                majority = freq;
                res = nums[i];
            }
        }

        return res;
    }
}
```

## Attempt 3: Attempt 3
- **Status**: `Accepted`
- **Date**: `2026-10-19 12:57:00 UTC`

### Submissions
#### Submission 1 (Java)
- **Result**: `Accepted` | **Runtime**: `15.0 ms` | **Memory**: `52.6 MB`
- **Timestamp**: `2026-03-25 17:23:30 UTC`

```java
import java.util.HashMap;

class Solution {
    public int majorityElement(int[] nums) {
        int nBy2 = nums.length / 2;

        HashMap<Integer, Integer> map = new HashMap<Integer, Integer>();
        
        for(int i = 0; i < nums.length; i++){
            if(map.containsKey(nums[i])){
                map.replace(nums[i], map.get(nums[i]) + 1);
            }else{
                map.put(nums[i], 1);
            }
        }

        for (Map.Entry<Integer, Integer> entry : map.entrySet()) {
            if(entry.getValue() > nBy2) return entry.getKey();
        }

        return -1;
    }
}
```
