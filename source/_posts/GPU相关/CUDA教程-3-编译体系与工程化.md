---
title: CUDA编程教程(3)：编译体系与工程化
categories:
  - GPU相关
tags:
  - CUDA
  - nvcc
  - PTX
  - CMake
  - 编译
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg3.png
excerpt: 从 nvcc 编译流水线到 CMake 集成 CUDA 项目，覆盖 PTX/SASS 的区别、常用编译选项和工程目录结构，目标是能独立构建和修改现有的 CUDA 项目。
series: CUDA编程教程
series_order: 3
---

> **系列导航**：[1. GPU架构与编程模型](CUDA教程-1-GPU架构与编程模型) | [2. 内存模型与优化](CUDA教程-2-内存模型与优化) | [4. 调试与错误排查](CUDA教程-4-调试与错误排查) | [5. 经典算子阅读修改](CUDA教程-5-经典算子阅读修改)

这篇文章的目标很具体：**拿到一个你不熟悉的 CUDA 项目，能把它编译起来，能看懂编译选项在做什么，能修改代码后正确重新构建。**

---

## 拿到陌生项目的紧急指南

```bash
# 1. 先看 CMakeLists.txt
grep -n "CMAKE_CUDA\|CUDA_ARCH\|\.cu\|find_package.*CUDA" CMakeLists.txt

# 2. 看 GPU 架构对不对
nvidia-smi --query-gpu=compute_cap --format=csv
# 输出如 8.6 → 对应 sm_86

# 3. 直接试编译
mkdir build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release
# 根据报错调整，常见问题见下文"编译常见报错"

# 4. 编译成功后，记得至少跑一次
compute-sanitizer --tool memcheck ./your_app
```

---

## nvcc 编译流水线

nvcc 不是直接把 `.cu` 变成可执行文件。它内部经历多个阶段：

```
.cu 文件
  │
  ├─[nvcc 预处理]──→ .cu.cpp (展开宏、处理 #include)
  │
  ├─[cudafe]───────→ 分离 host 代码和 device 代码
  │
  ├─[host 路径]────→ gcc/clang 编译 C++ 部分 → .o
  │
  └─[device 路径]──→ cicc 编译 CUDA C → PTX → ptxas 汇编 → SASS → cubin
                         │                    │
                         │                    └── 嵌入 host .o 作为 fatbinary
                         └── 也可保留 .ptx 文件（-keep 选项）
```

**三个关键中间产物**：

| 产物 | 含义 | 怎么看到 |
|---|---|---|
| PTX (.ptx) | GPU 汇编的中间表示，**跨 GPU 架构通用** | `nvcc -ptx` 或 `--keep` |
| SASS | 具体 GPU 架构的机器码，**架构相关** | `cuobjdump -sass a.out` |
| cubin (.cubin) | 二进制 ELF，包含 SASS | `--keep` 可保留 |

---

## 常用编译选项速查

### 必知的选项

```bash
# 指定目标 GPU 架构（生成对应 SASS）
nvcc -arch=sm_80  source.cu   # A100
nvcc -arch=sm_86  source.cu   # RTX 3090
nvcc -arch=sm_89  source.cu   # RTX 4090 / L40S
nvcc -arch=sm_90a source.cu   # H100 (a = 支持 sm_90 的架构变体)

# 同时生成多架构（fat binary，兼容多代 GPU）
nvcc -gencode arch=compute_80,code=sm_80 \
     -gencode arch=compute_86,code=sm_86 \
     source.cu

# 调试模式（-G 关掉 device 优化，-g 加 host+device 符号）
nvcc -G -g source.cu -o debug_build

# 看编译器做了什么
nvcc --ptxas-options=-v source.cu   # 寄存器用量和 smem 用量
nvcc --keep source.cu               # 保留所有中间文件 (.ptx, .cubin, .o)

# 分离编译
nvcc -c kernel1.cu -o kernel1.o
nvcc -c kernel2.cu -o kernel2.o
nvcc kernel1.o kernel2.o -o program

# 性能相关
nvcc -O3 --use_fast_math source.cu       # 高性能，牺牲少许精度
nvcc -lineinfo source.cu                 # 保留行号信息（profiler 需要）
nvcc --resource-usage source.cu          # 打印 resource usage 不实际编译
```

### GPU 架构代号速查

| compute_cap | 架构代号 | 代表 GPU |
|---|---|---|
| 7.0 | sm_70 | V100 |
| 7.5 | sm_75 | RTX 2080 Ti, T4 |
| 8.0 | sm_80 | A100 |
| 8.6 | sm_86 | RTX 3090/3080 |
| 8.9 | sm_89 | RTX 4090/4080, L40S |
| 9.0a | sm_90a | H100 |

```bash
nvidia-smi --query-gpu=compute_cap --format=csv  # 查当前 GPU
```

---

## CMake 集成 CUDA 项目

### 直接可用的 CMakeLists.txt 模板

```cmake
cmake_minimum_required(VERSION 3.18)
project(my_cuda_project LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_ARCHITECTURES 80 86 89)           # 多个架构 → fat binary
set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)          # 跨 .cu 调用 __device__ 必备

# Release 编译选项
set(CMAKE_CUDA_FLAGS_RELEASE "${CMAKE_CUDA_FLAGS_RELEASE} -O3 --use_fast_math -lineinfo")

add_executable(my_app
    src/main.cpp
    src/kernels/gemm.cu
    src/kernels/reduce.cu
)

target_include_directories(my_app PRIVATE include)
target_link_libraries(my_app PRIVATE cublas cudart)
```

### 编译

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### 关键配置项解释

```cmake
set(CMAKE_CUDA_ARCHITECTURES 80 86 89)
# → nvcc 会为 sm_80, sm_86, sm_89 各生成一份 SASS
# → binary 变大但兼容性最好

# "80-real" = 生成 sm_80 的 SASS
# "80-virtual" = 只生成 sm_80 的 PTX（运行时 JIT 编译，慢但 binary 小）

set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)
# 只有当你跨 .cu 文件调用 __device__ 函数时才需要
# 比如 gemm.cu 调了 reduce.cu 里的 __device__ 函数
# 如果所有 __device__ 函数都在同一个 .cu 或在 .cuh 头文件里 inline → 不需要
```

---

## 编译常见报错与秒修

### 错误 1: 架构不匹配

```
CUDA error: no kernel image is available for execution on the device
```

在 A100 上跑了 sm_86 编译的 binary，或在 3090 上跑了 sm_80 的。修：

```bash
# 查架构 → 重新编译
nvidia-smi --query-gpu=compute_cap --format=csv
nvcc -arch=sm_80 kernel.cu   # 或者用 fat binary
```

### 错误 2: `.cpp` 里写了 CUDA 代码

```
error: identifier "cudaMalloc" is undefined
error: expected expression before '<' token  (指 <<<>>>)
```

修：文件改名为 `.cu`，或在 CMake 里标记：
```cmake
set_source_files_properties(wrapper.cpp PROPERTIES LANGUAGE CUDA)
```

### 错误 3: 跨文件缺定义

```
ptxas fatal: Unresolved extern function '_Z7my_funcf'
```

`__device__` 函数在 A.cu 定义但在 B.cu 调用，没开 separable compilation。修：
```cmake
set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)
# 或者把函数定义移到 .cuh 头文件里 inline
```

### 错误 4: host/device 函数混用

```
error: calling a __host__ function from a __global__ function
```

kernel 里调了 CPU 函数。修：加 `__host__ __device__` 标记，或写 device 版本。

### 错误 5: 越界访问

运行期 crash / 结果 NaN。第一时间跑：
```bash
compute-sanitizer --tool memcheck ./my_app
```

---

## PTX 阅读：调试和验证的工具

```bash
nvcc -ptx kernel.cu -o kernel.ptx
# 或
cuobjdump --dump-ptx a.out
```

不需要手写 PTX，但看 PTX 能回答这些问题：

```ptx
// 一个 vectorAdd kernel 的 PTX（nvcc -ptx 的输出）
.visible .entry _Z9vectorAddPKfS0_Pfi(
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_0,
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_1,
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_2,
    .param .u32 _Z9vectorAddPKfS0_Pfi_param_3
)
{
    .reg .f32   %f<4>;        // 浮点寄存器（只有4个，说明编译器没spill）
    .reg .b32   %r<10>;       // 整数寄存器
    .reg .b64   %rd<8>;       // 64位地址寄存器

    ld.param.u64    %rd1, [_Z9vectorAddPKfS0_Pfi_param_0];
    cvta.to.global.u64  %rd2, %rd1;
    ld.global.f32   %f1, [%rd2];    // ← 从global memory读float
    ld.global.f32   %f2, [%rd3];    // ← 两次ld.global = 两次global读
    add.f32     %f3, %f1, %f2;      // ← 如果这是 mul+add, 说明没触发FMA
    st.global.f32   [%rd4], %f3;    // ← 一次global写
    ret;
}
```

| 你想知道的 | 在 PTX 里找 | 上例的结论 |
|---|---|---|
| 循环展开了吗 | `bra` 指令的数量和位置 | 没有循环 → 编译器展开了 |
| 用了 FMA 吗 | `fma.rn.f32` vs `mul.f32` + `add.f32` | 只有 `add.f32`，没有 FMA（这个kernel不涉及乘加） |
| 不必要的 global 访存 | `ld.global` 和 `st.global` 数量 | 2读1写 → 合理 |
| 寄存器用量 | 头部 `.reg` 声明 | 只有4个浮点寄存器，无spill |
| shared memory 用了吗 | `ld.shared` / `st.shared` 指令 | 没用到 |
| 编译器理解了我的 `__syncthreads()` 吗 | `bar.sync` 指令 | 这个kernel没有barrier |

---

## `.cuh` vs `.h`

CUDA 社区约定，不是强制的（编译器不关心），但帮你快速理解文件角色：

```cuda
//=== cuda_utils.cuh — 包含 device 函数声明 ===
#pragma once
#include <cuda_runtime.h>

__global__ void my_kernel(float *data, int n);
__device__ float helper_func(float x);

// 可复用的工具宏
#define CUDA_CHECK(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, \
                cudaGetErrorString(err)); \
        exit(1); \
    } \
} while(0)
```

```cuda
//=== common.h — 纯 host 或两端通用 ===
#pragma once
#include <cstdio>

// host & device 都能调
inline __host__ __device__ int ceiling_div(int a, int b) {
    return (a + b - 1) / b;
}
```

---

## 生存技能总结

1. **能把项目编译起来**：看懂 CMake 里的 `CMAKE_CUDA_ARCHITECTURES`，知道怎么加正确的 `-arch`
2. **能看懂编译报错**：架构不匹配、host/device 混用、缺定义三种最常见
3. **能查寄存器用量**：`nvcc --ptxas-options=-v`
4. **能用 compute-sanitizer**：编译完第一件事跑 memcheck
5. **能生成 PTX**：验证编译器确实把你的循环展开了、确实用了 FMA

---

## 下篇文章

[第四篇：调试与错误排查实战](/GPU相关/CUDA教程-4-调试与错误排查/) — CUDA 最可怕的 10 种错误，从 "unspecified launch failure" 到 kernel 死锁，每种都有定位方法和修复套路。
