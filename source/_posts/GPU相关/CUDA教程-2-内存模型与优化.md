---
title: CUDA编程教程(2)：内存模型与CUDA代码写法
categories:
  - GPU相关
tags:
  - CUDA
  - GPU
  - 内存优化
  - Shared Memory
  - Coalescing
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg3.png
excerpt: 你已经知道寄存器、共享内存、全局内存的区别——本文告诉你这些在 CUDA 代码里怎么声明、怎么用、怎么排查最常见的性能问题。
series: CUDA编程教程
series_order: 2
---

> **系列导航**：[1. GPU架构与编程模型](CUDA教程-1-GPU架构与编程模型) | [3. 编译体系与工程化](CUDA教程-3-编译体系与工程化) | [4. 调试与错误排查](CUDA教程-4-调试与错误排查) | [5. 经典算子阅读修改](CUDA教程-5-经典算子阅读修改)

GPU 内存层级：寄存器最快，shared memory 次之，global memory 最慢。下面直接看每种内存在 CUDA 里怎么声明、怎么写、怎么排查问题。

---

## 各种内存在代码里长什么样

```
速度: 寄存器 >> Shared Memory >> Constant >> Global (HBM)

声明方式:
  float x;                     // 局部变量 → 编译器尽量放寄存器
  __shared__ float tile[256];  // block 内共享，SM 的 SRAM 上
  __constant__ float w[64];    // 全局只读，带专用 cache
  cudaMalloc(&ptr, bytes);     // HBM，所有 SM 可读写
```

目标：**把频繁复用的数据从 Global 搬到 Shared 或寄存器，每搬一级延迟降 5-10 倍。**

---

## Global Memory：Coalesced Access

### 规则极简版

> **同一个 warp 的 32 个线程，如果访问的物理地址在 128 字节连续范围内，就能合并成 1 次 memory transaction。**

```cuda
// ✅ stride-1：coalesced。thread i 读 a[i]
float x = a[blockIdx.x * blockDim.x + threadIdx.x];

// ✅ stride-1（矩阵按行）：coalesced
int row = blockIdx.x;
float x = matrix[row * N + threadIdx.x];  // 连续线程读同一行相邻列

// ❌ stride-N（矩阵按列）：非 coalesced，灾难
float x = matrix[threadIdx.x * N + col];  // 连续线程读不同行的同一列
// 后果：带宽利用率可能从 90% 掉到 3%
```

### 为什么会掉那么多

A100 HBM 带宽约 2 TB/s，但只有 coalesced 访问才接近这个数字。stride-N 访问让每次 transaction 只用到 cache line 里的 4 bytes，其余 124 bytes 浪费了——32 次 transaction 只读了你需要的 128 bytes，有效带宽 / 实际传输 ≈ 1/32。

### 修复方案

**方案 A：SoA 替代 AoS**
```cuda
// 不要用
struct Particle { float x, y, z, vx, vy, vz; };  // AoS，warp 内无法 stride-1

// 改用
float *px, *py, *pz, *pvx, *pvy, *pvz;   // SoA，每个数组都 stride-1
```

**方案 B：Shared Memory 转置**

---

## Shared Memory

### 声明和使用

```cuda
__global__ void tiled_kernel(const float *in, float *out, int n) {
    __shared__ float tile[256];

    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + threadIdx.x;

    // 协作加载
    tile[tid] = (gid < n) ? in[gid] : 0.0f;
    __syncthreads();

    // 在 shared memory 上反复计算
    float acc = 0;
    for (int i = 0; i < 256; i++) acc += tile[i];

    if (gid < n) out[gid] = acc;
}
```

假设每个元素被 block 内所有线程读了 N 次。不用 shared memory：N × 400 cycles。用了 shared memory：400 + N × 30 cycles。

### Dynamic Shared Memory

```cuda
// launch 时指定大小
kernel<<<grid, block, tile_size * sizeof(float)>>>(...);

// kernel 内
extern __shared__ float tile[];
```

### Bank Conflict

Shared memory 按 4 字节切分成 32 个 bank。同一 warp 访问同一 bank 的不同地址 → 串行。

```cuda
// ❌ thread i 读 tile[32 * i]：所有线程命中 bank 0 → 32-way conflict
float x = tile[threadIdx.x * 32];

// ✅ stride-1：无冲突
float x = tile[threadIdx.x];

// ✅ 修复：padding
__shared__ float tile[32][32 + 1];  // 32+1=33，33和32互质 → 冲突消失
```

规则：block 内按 `threadIdx.x` 递增的访问不要产生 stride 为 32 倍数的地址间隔。产生了就加 padding。

---

## Constant Memory

```cuda
__constant__ float weights[256];  // 最多 64 KB
cudaMemcpyToSymbol(weights, h_weights, sizeof(weights));
```

warp 内所有线程读**同一地址** → 1 cycle 广播。读不同地址 → 退化为串行。

适用：卷积核权重、scale/bias 等 warp 内一致的参数。

---

## Tiling 实战：GEMM

### Naive 版本

```cuda
__global__ void matmul_naive(const float *A, const float *B, float *C, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < N && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < N; k++) {
            sum += A[row * N + k] * B[k * N + col];
        }
        C[row * N + col] = sum;
    }
}
```

A（stride-1 ✓），B（stride-N ✗）。

### Tiled 版本

```cuda
#define TILE 16

__global__ void matmul_tiled(const float *A, const float *B, float *C, int N) {
    __shared__ float As[TILE][TILE];
    __shared__ float Bs[TILE][TILE];

    int row = blockIdx.y * TILE + threadIdx.y;
    int col = blockIdx.x * TILE + threadIdx.x;

    float sum = 0.0f;

    for (int t = 0; t < (N + TILE - 1) / TILE; t++) {
        int a_col = t * TILE + threadIdx.x;
        As[threadIdx.y][threadIdx.x] =
            (row < N && a_col < N) ? A[row * N + a_col] : 0.0f;

        int b_row = t * TILE + threadIdx.y;
        Bs[threadIdx.y][threadIdx.x] =
            (b_row < N && col < N) ? B[b_row * N + col] : 0.0f;

        __syncthreads();

        for (int k = 0; k < TILE; k++) {
            sum += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        }
        __syncthreads();
    }

    if (row < N && col < N) C[row * N + col] = sum;
}
```

每个 global 读被 256 个线程复用，global read / 16。B 的 stride-N 也解决了（搬到 shared 后 stride-1）。

| | Global read | B 模式 | 估算带宽 |
|---|---|---|---|
| Naive | 2N³ | stride-N | ~50 GB/s |
| Tiled 16×16 | 2N³/16 | stride-1 | ~1.2 TB/s |

**tiling 不是在优化计算，是在优化访存。** 计算量没变，但计算发生在离 ALU 近得多的存储层级上。

---

## Occupancy：从 Kernel 代码反推

Occupancy = SM 上活跃 warp / 最大 warp。从 kernel 代码直接算：

```bash
nvcc --ptxas-options=-v kernel.cu
# 输出: Used 64 registers, 8192 bytes smem
```

```
A100: 65536 regs/SM, 164 KB smem/SM, block=256 threads

每个 block:
  regs  = ceil(64 × 256 / 256) × 256 = 16384  (256-register 对齐)
  smem  = 8192 bytes = 8 KB

每个 SM 最多:
  regs 限制: 65536 / 16384 = 4 blocks
  smem 限制: 164 / 8 = 20 blocks
  → min = 4 blocks = 32 warps/SM

Occupancy = 32 / 64 = 50%
```

50% 对大部分 kernel 足够。提升方法：更小的 block（128）、减少 smem、`__launch_bounds__`。

---

## 实操 Checklist

```
□ global read/write 是 stride-1？
□ 复用 > 2 次的数据搬进 shared memory？
□ shared memory 有 stride-32 倍数的访问？（→ bank conflict）
□ 每次 shared write 后、read 前有 __syncthreads()？
□ 寄存器 spill 了？（--ptxas-options=-v）
□ occupancy > 50%？
```

---

## 下篇文章

[第三篇：编译体系与工程化](/GPU相关/CUDA教程-3-编译体系与工程化/) — nvcc 到底在干什么、CMake 怎么配 CUDA 项目、5 种最常见的编译错误和修复方法。
