---
title: CUDA编程教程(2)：内存模型与优化
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
excerpt: 深入 CUDA 内存层级：global memory coalescing 的数学条件、shared memory bank conflict 的原理与规避、constant memory 的广播机制，以及 tiling 策略如何把 global 访问量砍掉一个数量级。
---

第一篇搭好了编程模型。这一篇专题讲内存——CUDA 性能优化 90% 的工作都是在和内存打交道。

## 内存类型全景

```
Device 代码可见的内存（从快到慢）：

Register        ← 编译器自动分配，每个线程私有，最快
Shared Memory   ← __shared__ 声明，block 内共享，手动管理
Constant Memory ← __constant__ 声明，所有线程只读，有 cache
Texture Memory  ← 硬件插值 + 2D 空间局部性 cache，图像专用
Global Memory   ← cudaMalloc 分配，所有线程可读写，最慢
Local Memory    ← 寄存器溢出时编译器自动用的 global 备份，慢
```

> 记住一句话：**让数据尽可能靠近计算单元**。寄存器 > Shared Memory > L1 > L2 > HBM。距离每远一级，延迟大约翻 3-5 倍。

---

## Global Memory 与 Coalesced Access

Global Memory（HBM）是最大但也最慢的内存。访问它的关键规则是 **coalescing（合并访问）**——同一个 warp 的 32 个线程访问的地址如果连续且对齐，可以被合并成一次或几次 memory transaction。

### 什么算 Coalesced

以 128 字节对齐的 cache line（L2 cache line = 32 bytes，但 transaction 通常 32/64/128 bytes）为例：

```cuda
// ✅ Coalesced: warp 内线程访问连续地址
// thread i 读 a[i] → 32 threads 访问 128 bytes 连续空间 → 1 次 128B transaction
float x = a[threadIdx.x];

// ✅ Coalesced (stride-1): 按行访问矩阵的行
int row = blockIdx.x;
float x = matrix[row * width + threadIdx.x];

// ❌ Stride-N: warp 内线程按列访问，地址间隔 width*sizeof(float)
// 32 threads 访问 32 个不连续的 cache line → 32 次 transaction，带宽利用率 ~3%
float x = matrix[threadIdx.x * width + col];

// ❌ 不对齐: 起始地址不是 32/64/128 字节对齐 → 多一次 transaction
float x = a[threadIdx.x + 3];  // 如果 a 128B 对齐，+3 字节偏移导致跨 cache line
```

### 量化感受

A100 的 HBM 带宽约 2 TB/s。但这是**峰值**，只有 coalesced 访问才能接近。stride-N 访问可能只用到 50 GB/s，差了 40 倍。

```cuda
// 直观对比：stride-1 vs stride-N 的实际带宽
__global__ void read_stride1(const float *in, float *out, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < n) out[tid] = in[tid];  // stride-1, coalesced
}

__global__ void read_strideN(const float *in, float *out, int n, int stride) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int idx = tid * stride;
    if (idx < n) out[tid] = in[idx];  // stride-N, non-coalesced
}
```

### 结论

- **结构体数组（AoS）→ 数组结构体（SoA）**：把 `struct {float x,y,z;}` 换成 `float *x, *y, *z`，让 warp 访问 stride-1
- **矩阵按行优先存储**：gemm 时让连续的线程读同一行的相邻列
- **必要时用 Shared Memory 做转置**：把 stride-N 的读变成 shared memory 内的 stride-1 写

---

## Shared Memory：程序员的手动 Cache

Shared Memory 是 SM 上的 SRAM（~164 KB / SM on A100），比 global memory 快 20-30 倍。**这就是你手里最重要的优化工具。**

### 声明和使用

```cuda
__global__ void shared_mem_demo(const float *in, float *out, int n) {
    __shared__ float tile[256];  // block 内所有线程共享

    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + threadIdx.x;

    // 1. 协作加载：每个线程从 global 读一个元素到 shared
    if (gid < n) tile[tid] = in[gid];
    __syncthreads();  // 2. 等所有线程都加载完

    // 3. 在 shared memory 上做多次计算（避免反复读 global）
    float sum = 0;
    for (int i = 0; i < 256; i++) {
        sum += tile[i];  // 每次访问 ~30 cycles vs global 的 ~400 cycles
    }

    if (gid < n) out[gid] = sum;
}
```

### Bank Conflict

Shared Memory 被分成 32 个 bank，每个 bank 4 bytes 宽。同一 warp 的多个线程如果访问同一个 bank 的不同地址，就会产生 **bank conflict**——这些访问被串行化。

```
Bank 布局 (4-byte 粒度):
  bank 0: addr 0, 32, 64, 96, ...
  bank 1: addr 4, 36, 68, 100, ...
  ...
  bank 31: addr 124, 156, 188, ...

同一 bank 内的不同地址 → conflict
同一 bank 内的相同地址 → broadcast (无冲突)
```

```cuda
// ❌ 经典 bank conflict: stride-32 访问
// thread i 读 tile[i * 32] → 所有线程命中同一 bank → 32-way conflict
float x = tile[threadIdx.x * 32];

// ✅ 无冲突: stride-1
float x = tile[threadIdx.x];

// ✅ 无冲突: 加 padding 消除冲突
__shared__ float tile[256 + 16];  // +16 让 stride-32 的地址偏移到不同 bank
float x = tile[threadIdx.x * 33];  // 改为 stride-33
```

### Padding 消除 Bank Conflict 的原理

原始（每行 32 个 float，bank 数 = 32）：
```
行0: bank 0  1  2  ... 31
行1: bank 0  1  2  ... 31    ← thread 0 和 32 都命 bank 0
```

加 padding（每行 33 个 float）：
```
行0: bank 0  1  2  ... 31
行1: bank 1  2  3  ... 0     ← 偏移了一个 bank
行2: bank 2  3  4  ... 1
```

---

## Constant Memory：广播读

```cuda
__constant__ float weights[256];  // 最多 64 KB，所有线程只读

// host 端写
cudaMemcpyToSymbol(weights, h_weights, sizeof(h_weights));
```

特点：
- warp 内所有线程读**同一地址**时，一次广播完成（1 cycle）
- warp 内线程读**不同地址**时，串行化（和普通 global memory 一样慢）
- 有独立的 constant cache（~8 KB / SM）

适用场景：模型参数、卷积核权重——warp 内所有线程在同一时刻读同一个值的场景。

---

## Tiling：用 Shared Memory 砍 Global 访问量

以矩阵乘法为例，说明 tiling 如何减少 global memory 访问。

### 问题

两个 N×N 矩阵相乘，每个线程计算一个输出元素需要读 2N 个 global memory 元素。总共需要 `2N^3` 次 global 读。

### Naive 实现

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

问题：每个线程循环 N 次，每次读 A（stride-1, coalesced ✓）和 B（stride-N, 读一整列, ✗）。

### Tiled 实现

```cuda
#define TILE_SIZE 16

__global__ void matmul_tiled(const float *A, const float *B, float *C, int N) {
    __shared__ float As[TILE_SIZE][TILE_SIZE];
    __shared__ float Bs[TILE_SIZE][TILE_SIZE];

    int row = blockIdx.y * TILE_SIZE + threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + threadIdx.x;

    float sum = 0.0f;

    // 遍历所有 tile
    for (int t = 0; t < (N + TILE_SIZE - 1) / TILE_SIZE; t++) {
        // 协作加载 A 的 tile
        int a_col = t * TILE_SIZE + threadIdx.x;
        if (row < N && a_col < N)
            As[threadIdx.y][threadIdx.x] = A[row * N + a_col];
        else
            As[threadIdx.y][threadIdx.x] = 0.0f;

        // 协作加载 B 的 tile
        int b_row = t * TILE_SIZE + threadIdx.y;
        if (b_row < N && col < N)
            Bs[threadIdx.y][threadIdx.x] = B[b_row * N + col];
        else
            Bs[threadIdx.y][threadIdx.x] = 0.0f;

        __syncthreads();

        // 在 shared memory 上做 tile 内的乘加
        for (int k = 0; k < TILE_SIZE; k++) {
            sum += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        }
        __syncthreads();
    }

    if (row < N && col < N) C[row * N + col] = sum;
}
```

**效果量化**：

| | Global 读次数 | 实际带宽 |
|---|---|---|
| Naive | `2N^3` | ~50 GB/s（受 B 的 stride-N 限制） |
| Tiled (16×16) | `2N^3 / 16` | ~1.2 TB/s（接近峰值） |

tiling 把 global 访问量降了 16 倍——每个 tile 的元素被同一个 block 内所有线程复用，不再需要每个线程各自从 global 重读。

---

## 寄存器压力与 Occupancy

寄存器是最快的内存，但每个 SM 的寄存器总数是固定的（A100: 65536/SM）。一个线程用多少寄存器，直接决定了 SM 能放多少线程。

```bash
# 编译时查看寄存器用量
nvcc --ptxas-options=-v kernel.cu
# 输出类似: Used 64 registers, 8192 bytes smem
```

Occupancy 计算：
```
假设 kernel 用 V 个寄存器/线程，block 有 B 个线程
每个 block 需要的寄存器 = ceil(V * B / 256) * 256  (256-register 对齐)
最多放的 block/SM = 65536 / (ceil(V * B / 256) * 256)
最多放的 warp/SM = min(block/SM * B/32, 64)  (max warps/SM = 64 for A100)
Occupancy = active_warps / max_warps
```

经验值：
- Occupancy ≥ 50%：足够 latency hiding，继续减寄存器收益递减
- 每个线程 ≥ 128 个寄存器：可能占用过高，考虑拆分 kernel 或用 `__launch_bounds__`

```cuda
// 告诉编译器这个 kernel 的最大线程数，帮助它优化寄存器分配
__global__ __launch_bounds__(256, 2) void my_kernel(...) { ... }
// 256 = max threads per block, 2 = min blocks per SM
```

---

## Local Memory：隐形的性能杀手

Local memory 不是物理内存，是编译器在**寄存器不够用时**把变量 spill 到 global memory。对程序员透明，但性能代价巨大。

```cuda
// 这个 kernel 可能产生大量 local memory spill
__global__ void register_hungry() {
    float a0, a1, a2, ..., a127;  // 128 个寄存器，很容易溢出
    // ...
}
```

发现方法：
```bash
nvcc --ptxas-options=-v kernel.cu
# 看到 "xx bytes stack frame, xx bytes spill stores, xx bytes spill loads" 就要警惕
```

解决方案：
- 减小 block 大小（给每个线程更多寄存器配额）
- 减少 kernel 内的局部变量
- 把 kernel 拆成多个更小的 kernel

---

## 内存优化的核心 checklist

1. **Global Memory 访问是 coalesced 的吗？** 不同 warp 的线程访问同一行相邻列 = coalesced。访问列 = 灾难。
2. **有没有用 Shared Memory 做 tiling？** 数据复用 ≥2 次就值得搬到 shared memory。
3. **Shared Memory 有没有 bank conflict？** 检查 stride-32 访问模式，必要时加 padding。
4. **Occupancy 够用吗？** 用 `ncu`（NVIDIA Nsight Compute）实测，不要猜。
5. **寄存器 spill 了吗？** 看 `--ptxas-options=-v` 的输出。

---

## 下一篇文章

第三篇讲编译体系与工具链：nvcc 的编译 pipeline（CUDA C → PTX → SASS）、常用编译选项、CMake 集成 CUDA 项目，以及如何阅读 PTX 代码来理解编译器的实际行为。
