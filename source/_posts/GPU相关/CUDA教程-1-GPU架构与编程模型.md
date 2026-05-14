---
title: CUDA编程教程(1)：GPU架构与编程模型
categories:
  - GPU相关
tags:
  - CUDA
  - GPU
  - 并行计算
  - 编程模型
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg3.png
excerpt: 从 GPU 硬件架构出发，系统讲解 CUDA 的线程层级（Grid/Block/Thread）、Warp 执行模型和 Kernel 启动语义，附带可运行的第一个 CUDA 程序和完整学习路线。
---

这是 CUDA 编程教程系列的第一篇。先给一条可执行的学习路线，再深入 GPU 硬件架构和 CUDA 编程模型。

## CUDA 学习路线

```
第 1-2 周：GPU 架构概念 + 第一个 Kernel
  理解 SM、Warp、线程层级 → 跑通 hello CUDA → 写 vectorAdd
  关键产出：能用 <<<grid, block>>> 启动 kernel，理解 threadIdx/blockIdx

第 3-4 周：内存模型
  Global memory coalescing → Shared memory bank conflict → Tiled matmul
  关键产出：能写 shared memory tiling，说出各级内存的带宽和延迟量级

第 5-6 周：编译与工具链
  nvcc pipeline → PTX/SASS 区别 → CMake 集成 → nvprof/nsys/ncu
  关键产出：能看 PTX 代码，能用 profiler 找瓶颈

第 7-8 周：经典算子 + 进阶特性
  Reduction / MatMul / Softmax 优化全流程 → Streams → Tensor Core
  关键产出：能写出接近 cuBLAS 70% 性能的 MatMul

第 9 周+：实战
  拿一个真实的 ML 算子（如 FlashAttention 简化版）端到端优化
  关键产出：完整的 GEMM/Attention kernel + profiling report
```

> 每阶段都要写代码。CUDA 只看不写约等于没学——很多问题（bank conflict、warp divergence、occupancy 不够）必须亲自踩一遍才有体感。

---

## GPU 硬件架构速览

写 CUDA 之前，需要理解代码跑在什么硬件上。

### 核心概念：SM（Streaming Multiprocessor）

GPU 由多个 SM 组成。以 A100 为例，108 个 SM。**SM 是调度的基本单元**——你 launch 一个 kernel，所有 block 会被分配到 SM 上执行。

SM 内部的核心资源（A100）：

| 资源 | 数量/规格 | 含义 |
|---|---|---|
| CUDA Cores (FP32) | 64 / SM | 每个时钟可执行 64 个 FP32 FMA |
| Tensor Cores | 4 / SM | 矩阵乘加专用单元 |
| Warp Scheduler | 4 / SM | 每个 SM 同时调度 4 个 warp |
| Register File | 65536 × 32-bit / SM | 所有线程的寄存器总和 |
| Shared Memory | 164 KB / SM (可配) | SM 内所有 block 共享 |
| L1 Cache | 与 Shared Mem 共用 | 自动缓存 global memory |
| Max Threads / SM | 2048 | 一个 SM 最多同时承载的线程数 |
| Max Blocks / SM | 32 | 一个 SM 最多同时承载的 block 数 |

### Warp：GPU 的基本执行单元

GPU 不是逐个线程执行的。**32 个线程组成一个 warp，warp 是 SM 上调度的最小单元。**

- 一个 warp 内的 32 个线程**同时执行同一条指令**（SIMT 模型）
- 如果 warp 内出现分支（if/else），不同分支的线程被**串行执行**（warp divergence），未激活的线程 idle
- 一个 block 被划分成若干个 warp，warp 之间独立调度

```
Block 有 256 threads → 8 warps
Block 有 128 threads → 4 warps
Block 的线程数必须是 32 的倍数（最好如此，不强制但强烈建议）
```

### 内存层级：从快到慢

```
寄存器 (Register)     ~0 延迟,   每个线程私有,  容量极少 (~255 个/线程)
Shared Memory         ~20-30 周期, Block 内共享,  ~164 KB/SM (A100)
L1 Cache              ~30 周期,   硬件自动管理,   与 Shared Mem 共用
L2 Cache              ~200 周期,  所有 SM 共享,   ~40 MB (A100)
Global Memory (HBM)   ~400-800 周期, 所有 SM 可访问, ~40-80 GB
```

理解这个层级是做优化的基础——**把数据从 Global Memory 搬到 Shared Memory 是做一次 tiling，减少 10-20 倍的访存延迟**。

---

## CUDA 编程模型：Thread / Block / Grid

CUDA 用三层结构组织线程：

```
Grid
 ├── Block 0
 │    ├── Thread (0,0,0)
 │    ├── Thread (1,0,0)
 │    └── ...
 ├── Block 1
 │    └── ...
 └── Block N-1
```

### 线程索引计算

这是写每个 kernel 都要用的公式，记住它：

```cuda
// 一维
int tid = blockIdx.x * blockDim.x + threadIdx.x;

// 二维（图像处理常用）
int x = blockIdx.x * blockDim.x + threadIdx.x;
int y = blockIdx.y * blockDim.y + threadIdx.y;
int idx = y * width + x;
```

### Kernel Launch 语法

```cuda
kernel_name<<<gridDim, blockDim, sharedMemBytes, stream>>>(args);
//             ^^^^^^  ^^^^^^^^  ^^^^^^^^^^^^^^  ^^^^^^
//             Block数 每Block   dynamic shared   异步流
//                     线程数    memory 大小      (可选)
```

- `gridDim` 可以是 `dim3`（三维），通常用 `dim3(numBlocks)` 或 `dim3(bx, by, bz)`
- `blockDim` 也是 `dim3`，常用 `dim3(256)` 或 `dim3(32, 8)`
- block 内线程数有限制：**≤ 1024**（所有 GPU），一般取 128/256/512
- grid 维度可以很大（最大 2^31-1）

---

## 第一个 CUDA 程序：Hello CUDA

```cuda
// hello.cu
#include <stdio.h>
#include <cuda_runtime.h>

__global__ void hello_kernel() {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int bdim = blockDim.x * gridDim.x;  // 总线程数
    printf("Hello from thread %d / %d\n", tid, bdim);
}

int main() {
    // 启动 2 个 block，每个 4 个线程 = 8 线程
    hello_kernel<<<2, 4>>>();
    cudaDeviceSynchronize();  // 等待 GPU 完成，否则 printf 可能来不及输出
    return 0;
}
```

编译和运行：

```bash
nvcc hello.cu -o hello
./hello
# Hello from thread 0 / 8
# Hello from thread 1 / 8
# ... (顺序不定，因为线程并行执行)
```

几个关键点：
- `__global__` 标记的函数是 kernel，从 host 调用、在 device 上执行
- `<<<grid, block>>>` 是 CUDA 扩展语法，C 标准里没有
- kernel 是**异步**的——`<<<>>>` 只是把任务提交到 GPU 队列，不等待完成
- `cudaDeviceSynchronize()` 阻塞 CPU 直到 GPU 完成所有任务

---

## 第二个程序：VectorAdd

hello world 之后的标准第二步——展示基本的 host/device 数据搬运和并行计算模式：

```cuda
// vector_add.cu
#include <stdio.h>
#include <cuda_runtime.h>

__global__ void vectorAdd(const float *a, const float *b, float *c, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < n) {
        c[tid] = a[tid] + b[tid];
    }
}

int main() {
    int n = 1 << 20;  // 1M elements
    size_t bytes = n * sizeof(float);

    // 1. Host 端分配内存
    float *h_a = (float*)malloc(bytes);
    float *h_b = (float*)malloc(bytes);
    float *h_c = (float*)malloc(bytes);
    for (int i = 0; i < n; i++) {
        h_a[i] = i * 1.0f;
        h_b[i] = i * 2.0f;
    }

    // 2. Device 端分配内存
    float *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, bytes);
    cudaMalloc(&d_b, bytes);
    cudaMalloc(&d_c, bytes);

    // 3. Host → Device 数据拷贝
    cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice);

    // 4. Launch kernel
    int threadsPerBlock = 256;
    int blocksPerGrid = (n + threadsPerBlock - 1) / threadsPerBlock;
    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);

    // 5. Device → Host 结果拷贝
    cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost);

    // 6. 验证
    bool ok = true;
    for (int i = 0; i < n; i++) {
        if (fabs(h_c[i] - (h_a[i] + h_b[i])) > 1e-5) { ok = false; break; }
    }
    printf("Result: %s\n", ok ? "PASS" : "FAIL");

    // 7. 释放内存
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
    free(h_a); free(h_b); free(h_c);
    return 0;
}
```

**完整的 host/device 交互模式**：

```
malloc (host)  →  cudaMalloc (device)  →  cudaMemcpy H2D  →  kernel<<<>>>  →  cudaMemcpy D2H  →  cudaFree  →  free
```

这个流程是几乎所有 CUDA 程序的骨架。kernel 可以有多个，但 host↔device 的搬运模式不变。

---

## Block 大小怎么选

不是一个随便的数。需要考虑两个硬件约束和两个性能因素：

### 硬件硬约束

1. **blockDim.x × blockDim.y × blockDim.z ≤ 1024**（所有 GPU）
2. **blockDim.x ≤ 1024, blockDim.y ≤ 1024, blockDim.z ≤ 64**（各维度上限）

### 性能软约束

3. **Warp 对齐**：block 内的线程数最好是 32 的倍数，否则最后一个 warp 有线程浪费
4. **Occupancy**：一个 SM 能同时驻留多少个 warp

Occupancy 的计算：

```
Occupancy = (active_warps_per_SM) / (max_warps_per_SM)

active_warps_per_SM 受三个因素限制：
  - 每个 block 用多少 register（越多，能放的 block 越少）
  - 每个 block 用多少 shared memory（同上）
  - 每个 SM 最多放多少个 block（硬件上限，通常 32）
```

**经验取值**（没有 profiler 时的起点）：

| 场景 | 推荐 blockDim |
|---|---|
| 一维数据处理（vector, reduction） | 256 |
| 二维图像处理 | dim3(32, 8) 或 dim3(16, 16) |
| 需要大量 shared memory 的 kernel | 128 或更小 |
| 计算密集、register 压力大 | 128（给更多 block 让 occupancy 上去） |

---

## 错误检查：CUDA API 的返回码

前面的代码为了简洁没加错误检查。实际开发中每个 CUDA API 调用都应该检查返回值：

```cuda
#define CUDA_CHECK(call) do {                                    \
    cudaError_t err = call;                                      \
    if (err != cudaSuccess) {                                    \
        fprintf(stderr, "CUDA error at %s:%d: %s\n",             \
                __FILE__, __LINE__, cudaGetErrorString(err));     \
        exit(EXIT_FAILURE);                                      \
    }                                                            \
} while(0)

// 用法
CUDA_CHECK(cudaMalloc(&d_a, bytes));
CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));

// Kernel 错误需要先 sync
vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);
CUDA_CHECK(cudaGetLastError());        // 检查 launch 错误
CUDA_CHECK(cudaDeviceSynchronize());   // 检查 kernel 执行错误
```

> `cudaGetLastError()` 抓 launch 配置错误（如 block 太大），`cudaDeviceSynchronize()` 后的 `cudaGetLastError()` 抓 kernel 运行期错误（如访存越界）。

---

## 统一内存（Unified Memory）简介

上面的 VectorAdd 显式管理了两份内存（host + device）。CUDA 也提供统一内存，让 CPU 和 GPU 访问同一块地址：

```cuda
float *a;
cudaMallocManaged(&a, bytes);  // 两边都能访问，driver 自动做 page migration

kernel<<<grid, block>>>(a, n);
cudaDeviceSynchronize();
// CPU 也能直接读 a，不用显式 cudaMemcpy
cudaFree(a);
```

**优点**：代码简单，不用手动 `cudaMemcpy`

**缺点**：page fault 按需迁移，首次访问 page 的延迟极高。对性能敏感的场景，显式管理内存仍然是主流

**适用场景**：快速原型、数据结构复杂的程序、懒得管理两套指针的时候

---

## 下一篇文章

第二篇会深入 CUDA 的内存模型：global memory coalescing、shared memory bank conflict、constant memory 的广播机制，以及如何用 tiling 把 global memory 访问量降一个数量级。

## 参考资源

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- PMPP book（Programming Massively Parallel Processors）—— CUDA 入门最好的书
- [NVIDIA CUDA Samples](https://github.com/NVIDIA/cuda-samples)
