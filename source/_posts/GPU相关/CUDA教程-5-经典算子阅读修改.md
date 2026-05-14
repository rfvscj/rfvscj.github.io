---
title: CUDA编程教程(5)：经典算子阅读与修改
categories:
  - GPU相关
tags:
  - CUDA
  - Reduction
  - MatMul
  - Softmax
  - 算子优化
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg3.png
excerpt: 拿到一个别人的 reduction/matmul/softmax kernel，能看懂每段在干什么，能在不改坏性能的前提下做局部修改。关键是学会读 kernel 的结构模式。
---

这篇的目标不是从零写优化 kernel，而是**拿到现有代码能看懂、能改、能不出 bug**。

---

## 阅读 Kernel 的通用策略

任何 kernel 都可以按这个顺序拆解：

```
1. 看函数签名：输入输出是什么，维度怎么传
2. 看线程索引：tid/row/col 怎么算的，这是所有访存的根
3. 看 shared memory 声明：哪些数据搬到了 smem，tile 多大
4. 看加载循环：数据从 global → shared 的 pattern
5. 看计算循环：在 shared/register 上做了什么
6. 看写回：结果从 register → global 的 pattern
7. 看边界处理：尤其是 n 不是 tile 倍数时怎么处理
```

---

## 算子一：Reduction（归约）

Reduction 是把数组归约成一个值（sum / max / norm）。几乎所有 ML 框架的 loss、normalization 都用到它。

### 能跑的 Naive 版本

```cuda
// 每个 block 归约一部分数据，结果存 partial[]
__global__ void reduce_naive(const float *input, float *partial, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int ti  = threadIdx.x;

    __shared__ float smem[256];

    // 1. 加载：每个线程读一个元素
    smem[ti] = (tid < n) ? input[tid] : 0.0f;
    __syncthreads();

    // 2. 归约：blockDim.x 次折半
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (ti < s) {
            smem[ti] += smem[ti + s];
        }
        __syncthreads();
    }

    // 3. 写回：只有线程 0 写 block 的部分和
    if (ti == 0) {
        partial[blockIdx.x] = smem[0];
    }
}
```

### 常见修改场景

**场景 A："把这个 sum reduction 改成 max reduction"**

只需要改两行：
```cuda
// 原来: smem[ti] += smem[ti + s];
// 改成: smem[ti] = fmaxf(smem[ti], smem[ti + s]);

// 原来: smem[ti] = (tid < n) ? input[tid] : 0.0f;
// 改成: smem[ti] = (tid < n) ? input[tid] : -INFINITY;  // max 的 identity
```

**场景 B："数组大小是动态的，不只 256 的倍数"**

在原代码中，`blockDim.x` 是编译期模板参数或固定值。要让 n 可变，关键是：
- 加载时的边界检查已经写好了：`(tid < n) ? input[tid] : 0.0f`
- 调用的地方需要处理 partial 数组的二次归约（如果 block 数 > 1）

```cuda
// 典型调用模式
int threads = 256;
int blocks = min((n + threads - 1) / threads, MAX_BLOCKS);
reduce_kernel<<<blocks, threads>>>(d_input, d_partial, n);

// 如果 blocks > 1，需要再调用一次 reduce_kernel 归约 partial
if (blocks > 1) {
    reduce_kernel<<<1, threads>>>(d_partial, d_result, blocks);
}
```

**场景 C："想加一个 scale/shift（如 RMSNorm 的 reduction）"**

在加载阶段改，不要动归约逻辑：
```cuda
// 原来: smem[ti] = (tid < n) ? input[tid] : 0.0f;
// 改成: 在 load 和 reduce 之间插一步
float val = (tid < n) ? input[tid] : 0.0f;
val = val * scale + shift;  // 加变换
smem[ti] = val * val;  // 如果要算平方和
__syncthreads();
// ... 后面的 reduction 不用动
```

---

## 算子二：GEMM（矩阵乘法）

### 能跑的 Tiled 版本（复习+注释版）

```cuda
#define TILE 16

__global__ void sgemm_tiled(
    const float *A, const float *B, float *C,
    int M, int N, int K)
{
    // --- 1. 线程索引 ---
    int row = blockIdx.y * TILE + threadIdx.y;  // C 的行 = A 的行
    int col = blockIdx.x * TILE + threadIdx.x;  // C 的列 = B 的列

    // --- 2. shared memory ---
    __shared__ float As[TILE][TILE];
    __shared__ float Bs[TILE][TILE];

    float sum = 0.0f;

    // --- 3. 遍历 K 维度的 tile ---
    for (int t = 0; t < (K + TILE - 1) / TILE; t++) {
        // 4a. 从 A 加载 tile: (row, t*TILE+tx)
        int a_col = t * TILE + threadIdx.x;
        As[threadIdx.y][threadIdx.x] =
            (row < M && a_col < K) ? A[row * K + a_col] : 0.0f;

        // 4b. 从 B 加载 tile: (t*TILE+ty, col)
        int b_row = t * TILE + threadIdx.y;
        Bs[threadIdx.y][threadIdx.x] =
            (b_row < K && col < N) ? B[b_row * N + col] : 0.0f;

        __syncthreads();

        // 5. tile 内乘加
        for (int k = 0; k < TILE; k++) {
            sum += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        }
        __syncthreads();
    }

    // --- 6. 写回 ---
    if (row < M && col < N) {
        C[row * N + col] = sum;
    }
}
```

### 阅读要点

- **为什么 `As[threadIdx.y][threadIdx.x]` 而不是 `As[threadIdx.x][threadIdx.y]`？**
  因为每个线程负责加载一个元素。`threadIdx.y` 和 `threadIdx.x` 组成 2D 映射，`As[ty][tx]` 对应 A 矩阵的 `(row, t*TILE+tx)` 位置。行由 ty 决定，列由 tx 决定。

- **为什么 tile 大小选 16？**
  16×16×4 bytes = 1024 bytes per tile。两个 tile 共用 2 KB. 远小于 shared memory 上限。更大的 tile 不一定更好——tile 越大，block 内线程数也要相应增大（16×16=256 线程），register 压力也会上升。

### 常见修改场景

**场景 A："把单精度改成半精度"**
```cuda
// 改函数签名 float* → half*
// 改 TILE 可能需要调：half 算力前提下，更大的 tile 可能更有利
// 如果有 Tensor Core 版本，直接切 cublas 或调 wmma
```

**场景 B："加 bias 和 ReLU"**
```cuda
// 在写回前加，不碰计算逻辑
if (row < M && col < N) {
    float val = sum + bias[row];  // 加 bias
    C[row * N + col] = val > 0 ? val : 0;  // ReLU
}
```

**场景 C："A 矩阵是转置的（A^T × B）"**
```cuda
// 改 A 的加载索引即可
// 原来: A[row * K + (t*TILE + tx)]     // A 行优先
// 转置后: A[(t*TILE + tx) * M + row]  // A^T 列优先
// 其他全部不变
As[threadIdx.y][threadIdx.x] =
    (row < M && a_col < K) ? A[a_col * M + row] : 0.0f;
```

> 这个场景非常常见。很多模型里 weight 是按列存还是按行存，跟你要的 GEMM 顺序不一致。只需要改 A 或 B 的**索引计算**，kernel 结构不变。

---

## 算子三：Softmax

### 安全 Softmax 的标准公式

$$
\text{softmax}(x_i) = \frac{e^{x_i - \max(x)}}{\sum_j e^{x_j - \max(x)}}
$$

减去 max 是为了数值稳定性（否则 e^100 直接 inf）。

### 能跑的 Kernel

```cuda
// 每行独立做 softmax，每个 block 处理一行
__global__ void softmax_per_row(const float *input, float *output, int cols) {
    int tid = threadIdx.x;
    __shared__ float smem[1024];

    int row_start = blockIdx.x * cols;

    // 1. 加载到 shared memory
    smem[tid] = (tid < cols) ? input[row_start + tid] : -INFINITY;
    __syncthreads();

    // 2. 找 max（这实际上是一个 1-block 的 max reduction）
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s && tid + s < cols) {
            smem[tid] = fmaxf(smem[tid], smem[tid + s]);
        }
        __syncthreads();
    }
    float row_max = smem[0];
    __syncthreads();

    // 3. 恢复数值，算 exp 并再加载到 smem
    float val = (tid < cols) ? expf(input[row_start + tid] - row_max) : 0.0f;
    smem[tid] = val;
    __syncthreads();

    // 4. sum reduction
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s && tid + s < cols) {
            smem[tid] += smem[tid + s];
        }
        __syncthreads();
    }
    float row_sum = smem[0];
    __syncthreads();

    // 5. 归一化写回
    if (tid < cols) {
        output[row_start + tid] = expf(input[row_start + tid] - row_max) / row_sum;
    }
}
```

### 阅读要点

- **为什么同一个 smem 数组被反复使用？** 因为 shared memory 很宝贵。max → exp → sum → 正常化，每一步都可以复用同一个缓冲区，只需 `__syncthreads()` 保证写后读。
- **为什么 `row_max` 和 `row_sum` 需要从 `smem[0]` 读出来放在寄存器里？** 因为后续的 `__syncthreads()` 会等所有线程，但只要数据已经在寄存器里就不怕被覆盖。

### Online Softmax（知其存在，面试会问）

上面的方式是 **3-pass**：一次找 max、一次算 sum、一次写回。每次都要重新从 global 读数据。

Online Softmax 只用 **1-pass**：

```cuda
// 核心思想：同时维护 running max 和 running sum
// 每处理一个新元素，用旧的 max 修正旧的 sum
float old_max = current_max;
current_max = fmaxf(current_max, new_val);
current_sum = current_sum * expf(old_max - current_max) + expf(new_val - current_max);
```

实际工程中，FlashAttention 的核心就用到了这个技巧。如果你需要理解 FlashAttention 的 CUDA kernel，先搞懂 online softmax。

---

## 修改 Kernel 的安全原则

从一个能跑的 kernel 出发修改时：

1. **改动索引计算 → 检查越界**：改 `row*N + col` 变成 `col*M + row` 这类操作最容易出 bug。改完先跑 `compute-sanitizer`。

2. **改动 shared memory 用量 → 重算 occupancy**：加大 tile 或加缓冲区前确认不超硬件上限。

3. **加 `__syncthreads()` → 确认所有线程都能走到**：不能放在 `if (tid < N)` 分支里，除非条件对所有线程一致。

4. **改计算逻辑 → 对比数值**：拿小 tensor（M=N=K=16 或更小）跑旧代码和新代码，`torch.allclose` 确认一致。

5. **改数据类型 → 注意 align**：half 要 2 字节对齐，float4 要 16 字节对齐（vectorized load）。

---

## 判断"要不要自己写 kernel"的决策树

```
这个操作 cublas/cudnn/cutlass 有没有？
  ├─ 有 → 直接用，别写
  └─ 没有 → 能 fuse 到现有 kernel 里吗？
              ├─ 能 → 在现有 kernel 末尾加几行，别新开 kernel
              └─ 不能 → 这是一个新的访存密集型操作吗？
                          ├─ 是 → 写新 kernel，注意 tiling
                          └─ 否（计算密集型）→ 先写 naive kernel 测正确性
                                                       再考虑是否要优化
```

大多数时候你不需要写 kernel。更多时候你改的是索引或数值计算，不是整体架构。
