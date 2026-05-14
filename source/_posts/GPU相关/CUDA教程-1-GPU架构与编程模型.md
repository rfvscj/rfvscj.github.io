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
series: CUDA编程教程
series_order: 1
---

> **系列导航**：[2. 内存模型与优化](CUDA教程-2-内存模型与优化) | [3. 编译体系与工程化](CUDA教程-3-编译体系与工程化) | [4. 调试与错误排查](CUDA教程-4-调试与错误排查) | [5. 经典算子阅读修改](CUDA教程-5-经典算子阅读修改)

## 概念到代码

| GPU 概念 | CUDA 代码中对应 |
|---|---|
| GPU 有 N 个 SM | `<<<grid, block>>>` 的 grid 决定 block 数 |
| SM 以 warp 为单位调度（32 线程一组） | `block / 32` = 一个 block 拆成几个 warp |
| 延迟靠大量线程切换来隐藏 | grid 里的 block 数要远大于 SM 数 |
| Occupancy = 活跃 warp / 最大 warp | 取决于 blockDim、register 用量、shared memory |
| Shared memory 比 HBM 快一个数量级 | `__shared__` 声明的数组在 SM 的 SRAM 上 |
| HBM 带宽是瓶颈 | `cudaMalloc` 分配的是 HBM，coalesced 访问才能用满 |

---

## SM 资源：你写代码时需要记住的三个数字

以 A100 为例，每个 SM 有三项硬限制直接影响你的 kernel 参数选择：

```
寄存器总数 / SM:   65536 个 (32-bit)
Shared Memory / SM: 最大 ~164 KB
最大线程数 / SM:    2048
最大 Block / SM:    32
```

这三个数字和你的代码直接相关：

- **你用 `__shared__ float tile[4096]`** → 一个 block 占 16 KB shared memory → 每个 SM 最多放 164/16 ≈ 10 个 block
- **你的 block 有 512 个线程，每个线程用 64 个寄存器** → 一个 block 占 512×64=32768 寄存器 → 每个 SM 最多放 65536/32768 = 2 个 block
- **最终每个 SM 能放多少 block，取上面两条和硬件 block 上限的最小值**

这就是 occupancy 的计算——你之前从 profiler 里看到的是同一个东西，现在能从 kernel 代码自己推导了。

---

## 三层线程结构：Grid / Block / Thread

一个 CUDA kernel launch 本质上是一次"启动 N 个线程，每个线程执行同一段代码"：

```
kernel<<<grid, block>>>(args)

grid:  多少个 block
block: 每个 block 里多少个线程
总线程数: grid × block
```

线程索引公式（任何 kernel 都从这两行开始）：

```cuda
// 一维映射
int tid = blockIdx.x * blockDim.x + threadIdx.x;

// 二维映射（矩阵乘法常用）
int row = blockIdx.y * blockDim.y + threadIdx.y;
int col = blockIdx.x * blockDim.x + threadIdx.x;
```

`blockIdx`、`threadIdx`、`blockDim`、`gridDim` 是 CUDA 内置变量，不需要声明。类型都是 `dim3`（三维），但大部分场景只用 `.x`。

---

## 三种函数标签

```cuda
__global__   void kernel(...) { }   // host 调用，device 执行
__device__   void helper(...) { }   // device 调用，device 执行
__host__     void cpu_f(...)  { }   // host 调用，host 执行（默认，不加也行）
// 也可以合起来
__host__ __device__ void both(...) { }  // 两端都能调用
```

---

## 第一个程序：Hello CUDA

```cuda
// hello.cu
#include <stdio.h>
#include <cuda_runtime.h>

__global__ void hello_kernel() {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    printf("Hello from thread %d, block %d\n", tid, blockIdx.x);
}

int main() {
    hello_kernel<<<2, 4>>>();           // 2 blocks × 4 threads = 8 threads
    cudaDeviceSynchronize();            // 必须 sync，否则 printf 可能不输出
    cudaError_t err = cudaGetLastError();
    printf("Kernel done: %s\n", cudaGetErrorString(err));
    return 0;
}
```

```bash
nvcc hello.cu -o hello
./hello
```

几个必须记住的关键点：
- **kernel 是异步的**：`<<<>>>` 只是把任务提交到 GPU 队列，不等执行。不调用 `cudaDeviceSynchronize()` 或 `cudaMemcpy` 的话，程序可能在 kernel 跑完前就退出了
- **`__global__` 函数必须返回 void**
- **`.cu` 文件才能用 `<<<>>>` 语法**，`.cpp` 文件里编译器不认识

---

## 第二个程序：VectorAdd（完整 host↔device 流程）

```cuda
#include <stdio.h>
#include <math.h>
#include <cuda_runtime.h>

// ========== 错误检查宏，每个项目都要有 ==========
#define CUDA_CHECK(call) do {                              \
    cudaError_t err = call;                                \
    if (err != cudaSuccess) {                              \
        fprintf(stderr, "%s:%d: CUDA error: %s\n",         \
                __FILE__, __LINE__, cudaGetErrorString(err)); \
        exit(1);                                           \
    }                                                      \
} while(0)

#define CUDA_KERNEL_CHECK() do {                           \
    CUDA_CHECK(cudaGetLastError());                        \
    CUDA_CHECK(cudaDeviceSynchronize());                   \
} while(0)
// ===================================================

__global__ void vectorAdd(const float *a, const float *b, float *c, int n) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid < n) {
        c[tid] = a[tid] + b[tid];
    }
}

int main() {
    int n = 1 << 20;              // 1M elements
    size_t bytes = n * sizeof(float);

    // 1. host 分配
    float *h_a = (float*)malloc(bytes);
    float *h_b = (float*)malloc(bytes);
    float *h_c = (float*)malloc(bytes);
    for (int i = 0; i < n; i++) { h_a[i] = 1.0f * i; h_b[i] = 2.0f * i; }

    // 2. device 分配
    float *d_a, *d_b, *d_c;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));

    // 3. H2D 拷贝
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // 4. launch
    int blockSize = 256;
    int gridSize  = (n + blockSize - 1) / blockSize;
    vectorAdd<<<gridSize, blockSize>>>(d_a, d_b, d_c, n);
    CUDA_KERNEL_CHECK();

    // 5. D2H 拷贝
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    // 6. 验证
    for (int i = 0; i < n; i++)
        if (fabsf(h_c[i] - 3.0f * i) > 1e-5) { printf("FAIL at %d\n", i); return 1; }
    printf("PASS\n");

    // 7. 释放
    CUDA_CHECK(cudaFree(d_a)); CUDA_CHECK(cudaFree(d_b)); CUDA_CHECK(cudaFree(d_c));
    free(h_a); free(h_b); free(h_c);
    return 0;
}
```

这段代码是**所有 CUDA 程序的骨架**：

```
malloc → cudaMalloc → cudaMemcpy H2D → kernel<<<>>> → cudaMemcpy D2H → cudaFree → free
```

你可以直接把这段拷走，改 kernel 内容、不改外面的流程。这是接手任何 CUDA 项目后第一个要识别的模式。

---

## Block 大小怎么选

**硬约束**：`blockDim.x × blockDim.y × blockDim.z ≤ 1024`，各维度分别 ≤ (1024, 1024, 64)。

**经验起点**（拿到新任务时直接用）：

| 场景 | blockDim | 原因 |
|---|---|---|
| 一维向量 | 256 | 8 warps，occupancy 友好 |
| 二维矩阵（gemm 等） | dim3(16, 16) | 256 线程，正方形 tile |
| shared memory 吃紧 | 128 | 给更多 block 腾空间 |
| 寄存器压力大 | 128 或 64 | 同样原因 |

**核心理由**：block 太小（< 64）浪费 warp 槽位；block 太大（512+）在寄存器或 shared memory 紧的 kernel 上反而降低 occupancy。256 是大部分场景的安全起点。

---

## `__syncthreads()`：block 内的同步点

当 block 内多个线程协作时（比如大家一起加载数据到 shared memory），**所有人**必须先写完再去读：

```cuda
__shared__ float smem[256];
smem[threadIdx.x] = data[tid];   // 每个线程写自己的位置
__syncthreads();                  // 等所有人写完
float val = smem[(threadIdx.x + 1) % 256];  // 读邻居的
```

两条铁律：
1. `__syncthreads()` 必须被**同一个 block 内所有线程**执行到，不能放在分支里（除非分支条件对所有线程相同）
2. 写 shared memory 后、读 shared memory 前，中间必须有 `__syncthreads()`

---

## 统一内存：比显式管理省事，但不免费

```cuda
float *a;
cudaMallocManaged(&a, bytes);  // host 和 device 都能直接读写

kernel<<<grid, block>>>(a, n);
cudaDeviceSynchronize();
// CPU 直接读 a，不需要 cudaMemcpy
cudaFree(a);
```

**适合**：快速原型、懒得管两套指针的时候。
**不适合**：性能敏感场景——page fault 触发按需迁移，第一次访问的延迟比显式 `cudaMemcpy` 更难预测。

---

## 下篇文章

[第二篇：内存模型与优化](/GPU相关/CUDA教程-2-内存模型与优化/) — 你懂共享内存和全局内存的区别，但你在 CUDA 代码里怎么声明 `__shared__`？怎么判断一个访存是不是 coalesced？bank conflict 长什么样怎么修？occupancy 怎么从 kernel 代码反推？

## 参考

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- PMPP (Programming Massively Parallel Processors) — 目前最好的 CUDA 入门书
