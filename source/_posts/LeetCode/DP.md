---
title: DP
tags: []
categories:
  - LeetCode
date: 2023-02-24 09:31:06
---
### 概述
动态规划适用于**重叠子问题**的问题，动态规划只能应用于有最优子结构的问题。最优子结构的意思是局部最优解能决定全局最优解（对有些问题这个要求并不能完全满足，故有时需要引入一定的近似）。简单地说，**问题能够分解成子问题来解决。**
动态规划的关键在于找出**状态转移方程**。

### LeetCode 70 走楼梯

#### 题干

假设你正在爬楼梯。需要 n 阶你才能到达楼顶。

每次你可以爬 1 或 2 个台阶。你有多少种不同的方法可以爬到楼顶呢？


示例 1：

输入：n = 2
输出：2
解释：有两种方法可以爬到楼顶。
1. 1 阶 + 1 阶
2. 2 阶
示例 2：

输入：n = 3
输出：3
解释：有三种方法可以爬到楼顶。
1. 1 阶 + 1 阶 + 1 阶
2. 1 阶 + 2 阶
3. 2 阶 + 1 阶

#### 分析
每次可以走1或2步，记dp[i]为到第i个台阶的所有走法。那么显然可以在第i-1个台阶走一步到第i个台阶，也可以在第i-2个台阶走两步到第i个台阶。于是有递推式`dp[i] = dp[i-1] + dp[i-2]`
n = 0时，无意义，但是作为递推式中的可能存在，可以设为1，也可以不管，i从3起记。
n = 1时，1种走法。
n = 2时，2种走法。
于是代码可写为
```python
class Solution:
    def climbStairs(self, n: int) -> int:
        dp = [1] * (n + 1)  # 注意这种操作只能用于一维，用在二维上会导致各行同时变化
        if n <= 2:
            return n
        for i in range(2, n + 1):  # 注意范围，最终要落到dp[n]
            dp[i] = dp[i-1] + dp[i-2]
        return dp[n]
```
需要考虑到，dp[i]仅依赖于dp[i-1]和dp[i-2]，所以不必存储所有结果，可改写为
```python
class Solution:
    def climbStairs(self, n: int) -> int:
        pre1 = 1
        pre2 = 1
        cur = 1
        # n = 0 没有意义
        if n <= 2:
            return n
        for i in range(2, n + 1):
            cur = pre1 + pre2
            pre2 = pre1
            pre1 = cur
        return cur
```

### Leetcode 198 打家劫舍
#### 题干
你是一个专业的小偷，计划偷窃沿街的房屋。每间房内都藏有一定的现金，影响你偷窃的唯一制约因素就是相邻的房屋装有相互连通的防盗系统，如果两间相邻的房屋在同一晚上被小偷闯入，系统会自动报警。

给定一个代表每个房屋存放金额的非负整数数组，计算你 不触动警报装置的情况下 ，一夜之内能够偷窃到的最高金额。

示例 1：

输入：[1,2,3,1]
输出：4
解释：偷窃 1 号房屋 (金额 = 1) ，然后偷窃 3 号房屋 (金额 = 3)。
     偷窃到的最高金额 = 1 + 3 = 4 。
示例 2：

输入：[2,7,9,3,1]
输出：12
解释：偷窃 1 号房屋 (金额 = 2), 偷窃 3 号房屋 (金额 = 9)，接着偷窃 5 号房屋 (金额 = 1)。
     偷窃到的最高金额 = 2 + 9 + 1 = 12 。

#### 分析
设i间房最多偷dp[i]，对于每间房，可以选择偷或不偷。如果偷第i间，那么最多能偷dp[i-2]+m[i]；如果不偷，那么最多能偷dp[i-1]的钱。
所以得到状态转移方程`dp[i] = max(dp[i-1], dp[i-2] + m[i])`
于是易得代码
```python
class Solution:
    def rob(self, nums: List[int]) -> int:
        dp = [0] * (len(nums) + 1)
        dp[0] = 0
        dp[1] = nums[0]
        for i in range(2, len(nums) + 1):
            dp[i] = max(dp[i - 1], dp[i - 2] + nums[i-1])
        return dp[len(nums)]
```
同样，dp[i]只依赖于dp[i-1]和dp[i-2]，可改写为
```python
class Solution:
    def rob(self, nums: List[int]) -> int:
        pre1 = nums[0]
        pre2 = 0
        cur = pre1
        for i in range(1, len(nums)):
            cur = max(pre1, pre2 + nums[i])
            pre2 = pre1
            pre1 = cur
        return cur
```

### Leetcode 413 等差数列划分
#### 题干
如果一个数列 至少有三个元素 ，并且任意两个相邻元素之差相同，则称该数列为等差数列。

例如，[1,3,5,7,9]、[7,7,7,7] 和 [3,-1,-5,-9] 都是等差数列。
给你一个整数数组 nums ，返回数组 nums 中所有为等差数组的 子数组 个数。

子数组 是数组中的一个连续序列。

示例 1：

输入：nums = [1,2,3,4]
输出：3
解释：nums 中有三个子等差数组：[1, 2, 3]、[2, 3, 4] 和 [1,2,3,4] 自身。
示例 2：

输入：nums = [1]
输出：0
 
提示：

1 <= nums.length <= 5000
-1000 <= nums[i] <= 1000

#### 分析
因为要求是**连续**等差数列，所以如果nums[i-3], nums[i-2], nums[i-1]是等差的，如果nums[i]与前面构成了等差，那么如果连续地到第i-1个位置能构成x个连续等差数列，第i个位置就能构成2x+1个，其中x个是未加上nums[i]的，x个是整体右移一位，1是到nums[i]的整个连续等差数列。
需要注意：如果nums[i]与前面不能构成等差呢？**可能存在多个片段，所以不能直接存储到当前位置的所有可能。**
可以对每个位置，存储**因当前位置，额外带来的可能。**
对位置i，如果`nums[i] - nums[i-1] == nums[i-1] - nums[i-2]`，那么这里形成了一个连续等差数列，对于等差数列，每加一位长度，**每个长度的子集都会加一**，并且多一个全集，如
三连等差，l3 += 1, 0-> 1，增数1
四连等差，l3 += 1, 1 -> 2; l4 += 1, 0 -> 1，增数2
五连等差，l3 += 1, 2 -> 3; l4 += 1, 1 -> 2; l5 += 1, 0 -> 1，增数3
也就是`dp[i] = dp[i-1] + 1`，只存储**增数**，最后对所有位置的增数求和，即所有可能。
代码很简单
```python
class Solution:
    def numberOfArithmeticSlices(self, nums: List[int]) -> int:
        n = len(nums)
        dp = [0] * (n + 1)
        if n < 3:
            return 0
        for i in range(2, n):
            if nums[i] - nums[i - 1] == nums[i - 1] - nums[i - 2]:
                dp[i] = dp[i - 1] + 1  # 注意理解
        return sum(dp)
```

### Leetcode 64 最小路径和
#### 题干

给定一个包含非负整数的 m x n 网格 grid ，请找出一条从左上角到右下角的路径，使得路径上的数字总和为最小。

说明：每次只能向下或者向右移动一步。

示例 1：

![](../../images/Pasted%20image%2020230304153708.png)
输入：`grid = [[1,3,1],[1,5,1],[4,2,1]]
输出：7
解释：因为路径 1→3→1→1→1 的总和最小。
示例 2：

输入：`grid = [[1,2,3],[4,5,6]]
输出：12

提示：
m == grid.length
n == grid[i].length
1 <= m, n <= 200
0 <= grid[i][j] <= 100

#### 分析
或许可以用深度优先搜索，一旦所尝试路径大于已找到的路径，则剪枝
可以存储到达每个位置的最小路径
`dp[i][j] = min(dp[i-1][j], dp[i][j-1]) + grid[i][j]
加上边界处理，
最后取`dp[m][n]`即可
代码可写为
```python
class Solution:
    def minPathSum(self, grid: List[List[int]]) -> int:
        # 式子 dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
        m = len(grid)
        n = len(grid[0])
        line = [0] * n
        dp = [line.copy() for i in range(m)]  # 注意不能用line乘哦
        dp[0][0] = grid[0][0]
        for i in range(m):
            for j in range(n):
                if i == 0 and j == 0:
                    continue
                elif i == 0:
                    dp[i][j] = dp[i][j - 1] + grid[i][j]
                elif j == 0:
                    dp[i][j] = dp[i - 1][j] + grid[i][j]
                else:
                    dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
        return dp[m - 1][n - 1]
```
