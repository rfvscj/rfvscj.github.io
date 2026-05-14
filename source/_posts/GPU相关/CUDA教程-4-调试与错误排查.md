---
title: CUDA编程教程(4)：调试与错误排查实战
categories:
  - GPU相关
tags:
  - CUDA
  - 调试
  - compute-sanitizer
  - 排错
  - profiling
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg3.png
excerpt: 接手 CUDA 代码最恐惧的就是莫名其妙的 crash 和错结果。本文覆盖 CUDA 最常见的 10 类错误、compute-sanitizer/cuda-gdb 实战用法，以及拿到一个报错后的标准排查流程。
series: CUDA编程教程
series_order: 4
---

> **系列导航**：[1. GPU架构与编程模型](CUDA教程-1-GPU架构与编程模型) | [2. 内存模型与优化](CUDA教程-2-内存模型与优化) | [3. 编译体系与工程化](CUDA教程-3-编译体系与工程化) | [5. 经典算子阅读修改](CUDA教程-5-经典算子阅读修改)

CUDA 的错误信息往往很模糊——`unspecified launch failure`、segfault、结果全 0。这篇的目标：从错误信息反推具体哪行代码、哪个线程、什么原因。

---

## CUDA 错误排查的标准流程

遇到问题先从这 4 步开始，不要跳步：

```
1. compute-sanitizer（30 秒定位内存越界）
2. 检查 launch configuration（block/grid 是不是超出限制）
3. CUDA_CHECK 宏所有 CUDA API 调用（排除 driver 层问题）
4. 打印几个关键位置的 threadIdx/blockIdx 确认索引计算
```

---

## 常见错误 Top 10

### 1. `an illegal memory access was encountered`

最常见也最头疼的错误。

**典型场景**：
```cuda
__global__ void buggy(float *data, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    data[tid] = 0;  // 没有边界检查，tid 可能 ≥ n
}
```

**定位方法**：
```bash
compute-sanitizer --tool memcheck ./my_app
# 输出:
# ========= Invalid __global__ write of size 4
# =========     at 0x... in buggy(float*, int)
# =========     by thread (128,0,0) in block (1024,0,0)
# =========     Address 0x... is out of bounds
```

直接告诉你**哪个 kernel、哪个线程、哪个 block、读还是写、越界了多少**。

### 2. `too many resources requested for launch`

```
CUDA error: too many resources requested for launch
```

**原因**：launch config 需要的 shared memory 或寄存器超过了 SM 的物理上限。

**排查**：
```bash
# 看 kernel 用了多少资源
nvcc --ptxas-options=-v kernel.cu
# 输出: Used 128 registers, 49152 bytes smem
#       ↑ 49152 bytes = 48 KB，A100 上限 ~164 KB，所以不是这个
#       ↑ 128 registers × 256 threads = 32768 regs/block
#       ↑ A100 有 65536 regs/SM，所以放 1 block 就基本满了，放不下 2 个
#       ↑ 如果 grid 只有一个 block 那没问题
#       ↑ 但如果 grid 有多个 block，SM 只能放 1 个，剩下的排队
```

### 3. `invalid configuration argument`

```
CUDA error: invalid configuration argument
```

**原因**：block 维度超限（>1024 threads 或 z > 64）。

```cuda
// ❌
kernel<<<grid, 2048>>>(...);  // block > 1024
kernel<<<grid, dim3(1,1,65)>>>(...);  // z > 64

// ✅
kernel<<<grid, 1024>>>(...);
```

### 4. `unspecified launch failure`

最没信息量的错误。通常是 kernel 内部出了问题但错误没被正确传递。

**标准排查**：
```bash
# 第一步：compute-sanitizer
compute-sanitizer ./my_app

# 第二步：cuda-gdb 逐行执行
cuda-gdb ./my_app
(cuda-gdb) break buggy_kernel
(cuda-gdb) run
(cuda-gdb) step  # 逐 warp 看哪一行挂的
```

### 5. `no kernel image is available for execution on the device`

```
CUDA error: no kernel image is available for execution on the device
```

**原因**：编译的架构和运行的 GPU 不匹配。比如用 `-arch=sm_80` 编译但在 RTX 3090 (sm_86) 上跑。

**修复**：
```bash
# 查看当前 GPU 架构
nvidia-smi --query-gpu=compute_cap --format=csv

# 重新编译正确架构
nvcc -arch=sm_86 kernel.cu

# 或用 fat binary 兼容多个架构
nvcc -gencode arch=compute_80,code=sm_80 \
     -gencode arch=compute_86,code=sm_86 \
     kernel.cu
```

### 6. `__syncthreads()` 导致的死锁

```cuda
__global__ void deadlock() {
    if (threadIdx.x < 16) {
        __syncthreads();  // ❌ 只有 16 个线程执行到了这里
    }
    // 另外 16 个线程没遇到 __syncthreads()
    // → 前面的 16 个永远等不到 → 死锁
}
```

**规则**：`__syncthreads()` 必须在 block 内**所有线程都走到的路径上**。不能放在分支里（除非分支条件所有线程一致）。

```cuda
// ✅ 正确：条件为维度常量，编译器能保证所有线程走同一分支
if (blockDim.x > 64) { ... __syncthreads(); ... }
```

### 7. shared memory 忘写 `__syncthreads()`

```cuda
__global__ void no_barrier(float *in, float *out) {
    __shared__ float tile[256];
    tile[threadIdx.x] = in[threadIdx.x];
    // ❌ 漏了 __syncthreads()
    out[threadIdx.x] = tile[(threadIdx.x + 1) % 256];
    // 有些线程可能还没写入 tile，其他线程就读了
}
```

**症状**：结果偶尔正确偶尔错误（race condition），profiler 看不出问题。

### 8. `cudaMalloc` 返回 `out of memory`

```bash
# 查看 GPU 显存占用
nvidia-smi

# 查看进程级别的显存
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
```

常见原因：
- 上一个进程没释放显存（Python notebook 里最常见：没 del 变量、没 empty_cache）
- cudaMalloc 请求的大小算错了（bytes 当成了 elements）
- `cudaFree` 没执行到（提前 return/exception）

```cuda
// 常见 bug：把元素数当字节数
cudaMalloc(&d_a, n);  // ❌ n 是元素数，不是字节数
cudaMalloc(&d_a, n * sizeof(float));  // ✅
```

### 9. kernel 执行了但结果全 0

```bash
# 检查 kernel 是否真的被 launch 了
# 在 kernel 之后立即检查
err = cudaGetLastError();
if (err != cudaSuccess) printf("Kernel launch: %s\n", cudaGetErrorString(err));

# 常见原因：
# 1. grid/block dim 算错了（如 (n+255)/256 结果为 0）
# 2. 数据没正确 cudaMemcpy 到 device
# 3. kernel 里 if (tid < n) 条件把全部线程都过滤了
```

### 10. `cudaDeviceSynchronize` 卡住不动

**原因**：kernel 在 GPU 上死循环或卡住了。

```cuda
// 常见死循环场景
__global__ void hang() {
    while (true) {  // ❌
        // ...
    }
}

// 或 warp 级别的死锁
__global__ void hang2() {
    if (threadIdx.x == 0) {
        while (data[0] == 0) { /* spin */ }  // ❌ data[0] 永远不更新
    }
    __syncthreads();  // 永远等不到
}
```

---

## compute-sanitizer 实战

这是调试 CUDA 最重要的工具，必须会用。

```bash
# 内存检查（最常用）
compute-sanitizer --tool memcheck ./my_app

# 竞态条件检测
compute-sanitizer --tool racecheck ./my_app

# 初始化检查（访问未初始化数据）
compute-sanitizer --tool initcheck ./my_app

# 同步检查
compute-sanitizer --tool synccheck ./my_app
```

### 典型输出解读

```
========= COMPUTE-SANITIZER
========= Invalid __global__ write of size 4 bytes
=========     at 0xdeadbeef in my_kernel(float*, int)
=========     by thread (128,0,0) in block (512,0,0)
=========     Address 0x7fff80001000 is out of bounds
=========     Saved host backtrace up to driver entry point at kernel launch time
=========
========= ERROR SUMMARY: 1 error
```

| 字段 | 含义 |
|---|---|
| `thread (128,0,0)` | 出错的线程，`threadIdx.x=128` |
| `block (512,0,0)` | 出错的 block，`blockIdx.x=512` |
| `Address 0x... out of bounds` | 访问了超出分配范围的地址 |
| `size 4` | 写入了 4 字节（一个 float/int） |

拿到这些信息后，你就能倒推：
```
block(512,0,0) × blockDim + thread(128,0,0)
= 512 × 256 + 128 = 131200
```
如果数组只有 131072 个元素，那就是 131200 ≥ 131072，差的就是那 128 个线程的越界。

---

## cuda-gdb 基础用法

compute-sanitizer 找不到问题时，用 cuda-gdb 逐行调试。

```bash
# 编译调试版本
nvcc -G -g kernel.cu -o debug_app

# 启动
cuda-gdb ./debug_app
```

```gdb
# 在 kernel 入口设断点
(cuda-gdb) break my_kernel
(cuda-gdb) run

# 查看当前线程信息
(cuda-gdb) info cuda threads
# Block (0,0)   Thread (0,0,0)   Device 0

# 切换线程
(cuda-gdb) cuda thread (128,0,0)

# 查看寄存器/局部变量
(cuda-gdb) print threadIdx.x
(cuda-gdb) print blockIdx.x

# 继续执行
(cuda-gdb) continue
```

> **限制**：cuda-gdb 在 kernel 内的断点是 warp 级别的——一个 warp 的 32 个线程同时停在断点。你只能选一个线程查看状态。

---

## 打印调试：临时但有效的技巧

在一个大 kernel 里定位问题，最快的方法往往是打印：

```cuda
__global__ void debug_kernel(float *data, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    // 只在关键线程打印
    if (tid < 3 || tid > n - 4) {
        printf("thread %d: data[%d] = %f\n", tid, tid, data[tid]);
    }

    if (tid >= n) {
        printf("WARNING: thread %d is out of bounds (n=%d)\n", tid, n);
    }

    // ... 原来的逻辑
}
```

> kernel 中的 `printf` 输出到 stdout，但从 GPU 传回 host 有缓冲。确保最后调了 `cudaDeviceSynchronize()`。

---

## 调试工作流检查清单

```
□ 1. 先跑 compute-sanitizer memcheck（覆盖 50% 的问题）
□ 2. 确认 CUDA_CHECK 在每次 cudaMalloc/cudaMemcpy/kernel launch 后
□ 3. 确认 kernel launch 的 grid/block dims 不为 0
□ 4. 确认 blockDim ≤ 1024 且各维度不超限
□ 5. 确认 -arch 匹配当前 GPU
□ 6. 确认所有 cudaMemcpy 的 size（bytes vs elements）
□ 7. 确认 nvidia-smi 看到足够的空闲显存
□ 8. 在 kernel 开头加 printf 确认它被执行了
□ 9. 跑 racecheck 排除 data race
□ 10. 最后手段：cuda-gdb 单步
```

---

## 下篇文章

第五篇讲经典算子的阅读和修改——如何看懂别人写的 reduction/matmul/softmax kernel，以及最小改动的修改策略。
