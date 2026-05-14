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

你已经知道 GPU 内存层级：寄存器最快，shared memory 次之，global memory 最慢。你可能还在 nvprof 里看过各种内存指标。本文只做一件事：**把这些概念翻译成具体的 CUDA 声明、访存模式和优化手段。**

---

## 各类内存在代码里长什么样

```
速度: 寄存器 >> Shared Memory >> Constant >> Global (HBM)

声明方式:
  float x;                     // 局部变量 → 编译器尽量放寄存器
  __shared__ float tile[256];  // block 内共享，SM 的 SRAM 上
  __constant__ float w[64];    // 全局只读，带专用 cache
  cudaMalloc(&ptr, bytes);     // HBM，所有 SM 可读写
```

你的目标：**把频繁复用的数据从 Global 搬到 Shared 或寄存器，每搬一级延迟降 5-10 倍。**

---

## Global Memory：Coalesced Access 是唯一规则

你肯定知道"合并访问"这个词。这里讲**在代码里怎么判断一段访存是否是 coalesced 的。**

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

### 工程上最常见的修复

两种做法解决 stride-N 问题：

**方案 A：改数据排布（SoA 替代 AoS）**
```cuda
// 不要用
struct Particle { float x, y, z, vx, vy, vz; };  // AoS，warp 内无法 stride-1

// 改用
float *px, *py, *pz, *pvx, *pvy, *pvz;   // SoA，每个数组都 stride-1
```

**方案 B：用 Shared Memory 做转置**（见后面的 tiling 节）

---

## Shared Memory：你手里最重要的工具

### 声明和使用模板

```cuda
__global__ void tiled_kernel(const float *in, float *out, int n) {
    __shared__ float tile[256];   // 固定大小声明

    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + threadIdx.x;

    // Step 1: 协作加载（每个线程搬一个元素）
    tile[tid] = (gid < n) ? in[gid] : 0.0f;
    __syncthreads();             // 等所有线程写完

    // Step 2: 在 shared memory 上反复读（在这期间不碰 global memory）
    float acc = 0;
    for (int i = 0; i < 256; i++) acc += tile[i];

    // Step 3: 写回
    if (gid < n) out[gid] = acc;
}
```

这样做有什么效果？假设每个元素被 block 内所有线程读了 N 次。不用 shared memory：N 次 global read，约 400×N cycles。用了 shared memory：1 次 global read + N 次 shared read = 400 + 30×N cycles。

### Dynamic Shared Memory

如果你的 tile 大小是运行期决定的（比如不同模型不同维度）：

```cuda
// launch 时指定第三个参数（bytes）
kernel<<<grid, block, tile_size * sizeof(float)>>>(...);

// kernel 内声明
extern __shared__ float tile[];   // 大小由 launch 时的 sharedMemBytes 决定
```

### Bank Conflict：怎么看出来、怎么修

Shared memory 按 4 字节切分成 32 个 bank。同一 warp 内多个线程访问同一 bank 的不同地址 → 串行化。

能引发 bank conflict 的经典场景：

```cuda
// ❌ thread i 读 tile[32 * i]：所有线程命中 bank 0
float x = tile[threadIdx.x * 32];

// ❌ 转置读写：thread.x 写 tile[ty][tx]，再以 stride-32 读 tile[tx][ty]
```

修复——加 padding：
```cuda
// 原来: __shared__ float tile[32][32];
// 修复: 每行多一个不用的元素，打散 bank 映射
__shared__ float tile[32][32 + 1];  // 32+1=33，33 和 32 互质 → 冲突消失
```

**你不需要死记 bank 编号。写代码时遵守一条规则：block 内线程的连续访问模式（按 `threadIdx.x` 递增）不要产生 stride 等于 32 的倍数的地址间隔。如果不幸产生了，加 padding。**

---

## Constant Memory：用对场景有奇效

```cuda
__constant__ float weights[256];  // 声明（最多 64 KB）

// host 端写入
cudaMemcpyToSymbol(weights, h_weights, sizeof(weights));
```

适用场景极窄但效果极好：**warp 内所有线程同时读同一个值**——一次广播 1 cycle 完成。但如果 warp 内线程读不同地址，退化为串行（和 global memory 一样慢）。

典型用法：卷积权重、标量参数（scale、bias 等 warp 内一致的参数）。

---

## Tiling 实战：拿 GEMM 举例

这里不重复之前的完整 GEMM 代码（见[第五篇](CUDA教程-5-经典算子阅读修改)），只讲 tiling 的核心机制和效果。

### 问题

两个 N×N 矩阵相乘，naive 写法每个线程读 N 次 A + N 次 B，总共约 2N³ 次 global read。而且读 B 是 stride-N 的（非 coalesced）。

### Tiling 的解法

```
把 A 和 B 拆成 16×16 的小块（tile）：
1. block 内所有线程协作把一块 tile 从 global 搬到 shared（每个线程搬 1 个元素）
2. 在 shared memory 上做 tile 内的计算（所有线程复用这些数据）
3. 搬到下一个 tile

效果：每个 global 读被同一个 block 内 256 个线程复用了
     → global read 次数 / 16
     → 同时解决了 B 的 stride-N 问题（搬到 shared 后内部访问是 stride-1）
```

### 量化

| | Global read 量 | B 的访存模式 | 估算有效带宽 |
|---|---|---|---|
| Naive | 2N³ | stride-N | ~50 GB/s |
| Tiled 16×16 | 2N³/16 | shared memory stride-1 | ~1.2 TB/s |

**tiling 的正确 mental model**：不是在优化计算，是在优化访存。计算量没有变少，但你让计算发生在离 ALU 近得多的存储层级上。

---

## Occupancy：从 Kernel 代码反推

你肯定知道 occupancy 是什么——SM 上活跃 warp 占最大 warp 的比例。这里直接讲**怎么从 kernel 代码算出来。**

```bash
# 编译时看
nvcc --ptxas-options=-v kernel.cu
# 输出: Used 64 registers, 8192 bytes smem, 0 bytes lmem
```

然后算：
```
假设 A100: 65536 regs/SM, 164 KB smem/SM, block=256 threads

每个 block:
  regs  = ceil(64 × 256 / 256) × 256 = 16384  (256-register 对齐)
  smem  = 8192 bytes = 8 KB

每个 SM 最多放:
  regs 限制: 65536 / 16384 = 4 blocks
  smem 限制: 164 / 8 = 20 blocks
  → 取 min = 4 blocks = 4 × 8 warps = 32 warps/SM

Occupancy = 32 / 64 = 50%
```

**50% 对大部分 kernel 就够了**——SM 只需要足够的活跃 warp 来隐藏延迟，更多 warp 边际收益递减。

如果你想要更高 occupancy：
- 用更小的 block（128 而非 256）
- 减少 shared memory 使用
- 加 `__launch_bounds__(maxThreadsPerBlock, minBlocksPerSM)` 提示编译器优化寄存器

---

## 实操 Checklist

拿到一个 kernel，从内存角度检查：

```
□ 所有 global 读/写是 stride-1（coalesced）的吗？
□ 有没有大于 2 次复用的数据？→ 搬进 shared memory
□ shared memory 有没有 stride 为 32 倍数的访问？→ bank conflict
□ __syncthreads() 在每次 shared 写之后、读之前都有？
□ 寄存器 spill 了吗？（--ptxas-options=-v 看 stack frame/spill 提示）
□ occupancy > 50% 了吗？
```

---

## 下篇文章

[第三篇：编译体系与工程化](/GPU相关/CUDA教程-3-编译体系与工程化/) — nvcc 到底在干什么、CMake 怎么配 CUDA 项目、5 种最常见的编译错误和修复方法。
