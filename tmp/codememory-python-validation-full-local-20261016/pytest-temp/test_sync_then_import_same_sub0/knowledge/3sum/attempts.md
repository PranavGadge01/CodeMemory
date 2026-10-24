# Attempts History: 3Sum

## Attempt 1: Attempt 1
- **Status**: `Wrong Answer`
- **Date**: `2023-11-16 02:00:00 UTC`

### Submissions
#### Submission 1 (C++)
- **Result**: `Wrong Answer` | **Runtime**: `N/A` | **Memory**: `N/A`
- **Timestamp**: `2023-11-16 02:00:00 UTC`

```cpp
#include <vector>
class Solution {
public:
    std::vector<std::vector<int>> threeSum(std::vector<int>& nums) {
        return {};
    }
};
```

## Attempt 2: Attempt 2
- **Status**: `Accepted`
- **Date**: `2023-11-16 03:00:00 UTC`

### Submissions
#### Submission 1 (C++)
- **Result**: `Accepted` | **Runtime**: `32.0 ms` | **Memory**: `20.1 MB`
- **Timestamp**: `2023-11-16 03:00:00 UTC`

```cpp
#include <vector>
#include <algorithm>
class Solution {
public:
    std::vector<std::vector<int>> threeSum(std::vector<int>& nums) {
        std::sort(nums.begin(), nums.end());
        std::vector<std::vector<int>> res;
        for (int i = 0; i < nums.size(); ++i) {
            if (i > 0 && nums[i] == nums[i-1]) continue;
            int l = i + 1, r = nums.size() - 1;
            while (l < r) {
                int sum = nums[i] + nums[l] + nums[r];
                if (sum == 0) {
                    res.push_back({nums[i], nums[l], nums[r]});
                    while (l < r && nums[l] == nums[l+1]) l++;
                    while (l < r && nums[r] == nums[r-1]) r--;
                    l++; r--;
                } else if (sum < 0) l++;
                else r--;
            }
        }
        return res;
    }
};
```
