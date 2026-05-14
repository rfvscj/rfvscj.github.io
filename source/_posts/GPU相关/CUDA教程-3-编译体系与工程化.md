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
---

这篇文章的目标很具体：**拿到一个你不熟悉的 CUDA 项目，能把它编译起来，能看懂编译选项在做什么，能修改代码后正确重新构建。**

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

> **实用知识**：PTX 是你在代码里写 `__device__` 函数时编译器真正生成的中间语言。看 PTX 能帮你理解编译器到底做了什么（循环展开、寄存器分配等）。SASS 则是最终跑在硬件上的东西，`cuobjdump --dump-sass` 是理解性能的最后手段。

---

## 常用编译选项速查

```bash
nvcc -o output source.cu [options]
```

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

# 调试模式（-G 关掉优化，-g 加符号信息）
nvcc -G -g source.cu -o debug_build

# 优化级别
nvcc -O3 source.cu            # 默认 -O3（host code）
nvcc -O3 --use_fast_math      # 启用快速数学（牺牲精度换速度）

# 看编译器做了什么
nvcc --ptxas-options=-v source.cu   # 打印寄存器用量和 smem 用量
nvcc --keep source.cu               # 保留所有中间文件 (.ptx, .cubin, .o)

# 分离编译（多个 .cu 文件各自编译再链接）
nvcc -c kernel1.cu -o kernel1.o     # 只编译不链接
nvcc -c kernel2.cu -o kernel2.o
nvcc kernel1.o kernel2.o -o program # 链接
```

### GPU 架构代号速查表

| 架构代号 | 代表 GPU | 关键特性 |
|---|---|---|
| sm_70 | V100 | Tensor Core v1, HBM2 |
| sm_75 | RTX 2080 Ti, T4 | Turing Tensor Core (int8) |
| sm_80 | A100 | TF32, HBM2e, 2x FP32 |
| sm_86 | RTX 3090/3080 | GA102 |
| sm_89 | RTX 4090/4080, L40S | Ada Lovelace |
| sm_90a | H100 | FP8, TMA, DSM |

```bash
# 查当前 GPU 的架构
nvidia-smi --query-gpu=compute_cap --format=csv

# 或运行时获取
# cudaDeviceProp::major * 10 + cudaDeviceProp::minor
```

---

## CMake 集成 CUDA 项目

这是最实用的部分——实际项目不会手写 nvcc 命令。

### 最小 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.18)
project(my_cuda_project LANGUAGES CXX CUDA)

# 方法 1: enable_language (推荐)
enable_language(CUDA)
add_executable(my_app main.cpp kernel.cu)

# 方法 2: find_package (老式写法)
find_package(CUDA REQUIRED)
cuda_add_executable(my_app main.cpp kernel.cu)
```

### 实际项目中的标准写法

```cmake
cmake_minimum_required(VERSION 3.18)
project(cuda_project LANGUAGES CXX CUDA)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)

# 设置目标 GPU 架构
set(CMAKE_CUDA_ARCHITECTURES 80 86 89)

# CUDA separable compilation（如果用了 __device__ 跨文件调用）
set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)

# 编译选项
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -O3 --use_fast_math")
# 调试用
# set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -G -g")

add_executable(my_app
    src/main.cpp
    src/kernels/gemm.cu
    src/kernels/reduce.cu
)

target_include_directories(my_app PRIVATE include)
target_link_libraries(my_app PRIVATE
    # 如果有外部库
    cublas cudart
)
```

### 编译

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### 多架构 fat binary 的正确 CMake 写法

```cmake
# 指定多个架构
set(CMAKE_CUDA_ARCHITECTURES 80 86 89)

# 或者用 target 级别设置
set_target_properties(my_app PROPERTIES
    CUDA_ARCHITECTURES "80-real;86-real;89-real"
)
# "80-real" 表示生成 sm_80 的 SASS (不是 PTX)
# "80-virtual" 表示只生成 sm_80 的 PTX (JIT 编译)
```

---

## 编译常见报错与修复

### 问题 1: `error: identifier "cudaMalloc" is undefined`

**原因**：`.cpp` 文件里调了 CUDA API，而编译器不知道这是 CUDA 代码。

**修复**：
```cmake
# CMake 方式：把 .cpp 改 .cu，或
set_source_files_properties(wrapper.cpp PROPERTIES LANGUAGE CUDA)
```

### 问题 2: `error: kernel launch from a `__host__` function`

**原因**：你在普通 C++ 函数里写了 `kernel<<<>>>()`，但文件被当成 .cpp 编译。`<<<>>>` 是 CUDA 扩展语法，C++ 编译器不认识。

**修复**：改文件名为 `.cu`，或在 CMake 中标记文件为 CUDA 语言。

### 问题 3: `ptxas fatal: Unresolved extern function`

**原因**：`__device__` 函数声明了没定义，或跨 .cu 文件调用了 `__device__` 函数但没开 separable compilation。

**修复**：
```cmake
set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)
```
或者把被调用的 `__device__` 函数移到同一个 .cu 文件或头文件里。

### 问题 4: `error: calling a `__host__` function from a `__global__` function`

**原因**：kernel 里调了 CPU 函数（如 `printf` 以外的 C 标准库函数）。

**修复**：把被调用的函数标记为 `__host__ __device__`，或写一个 `__device__` 版本。

### 问题 5: Segfault / `an illegal memory access was encountered`

**原因**：kernel 访问了越界内存。

**修复思路**：
```bash
# 1. 用 compute-sanitizer 定位
compute-sanitizer ./my_app

# 2. 或用 cuda-memcheck（旧名）
cuda-memcheck ./my_app

# 输出会告诉你哪行代码、哪个线程访问了非法地址
```

---

## 如何阅读 PTX 代码

PTX 是理解编译器行为的关键。不需要精通，但应该能认得几个关键指令。

```bash
# 生成 PTX
nvcc -ptx kernel.cu -o kernel.ptx
# 或从已有 binary 提取
cuobjdump --dump-ptx a.out
```

### PTX 速读

```ptx
// 一个简单的 vector add kernel 的 PTX
.visible .entry _Z9vectorAddPKfS0_Pfi(   // kernel 入口
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_0,  // 参数
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_1,
    .param .u64 _Z9vectorAddPKfS0_Pfi_param_2,
    .param .u32 _Z9vectorAddPKfS0_Pfi_param_3
)
{
    // 寄存器
    .reg .f32   %f<4>;        // 浮点寄存器
    .reg .b32   %r<10>;       // 整数寄存器
    .reg .b64   %rd<8>;       // 64 位地址寄存器

    ld.param.u64    %rd1, [_Z9vectorAddPKfS0_Pfi_param_0];
    //  ↑加载函数参数

    cvta.to.global.u64  %rd2, %rd1;
    //  ↑转换为全局内存地址

    ld.global.f32   %f1, [%rd2];
    //  ↑从 global memory 加载 float

    add.f32     %f3, %f1, %f2;
    //  ↑浮点加法

    st.global.f32   [%rd4], %f3;
    //  ↑存回 global memory

    ret;
}
```

关键指令速查：

| PTX 指令 | 含义 |
|---|---|
| `ld.global.f32` | 从 global memory 读 float |
| `ld.shared.f32` | 从 shared memory 读 |
| `st.global.f32` | 写 float 到 global memory |
| `add.f32` | 浮点加 |
| `fma.rn.f32` | FMA (fused multiply-add)，Tensor Core 会用到 |
| `atom.add.f32` | 原子加 |
| `bar.sync` | `__syncthreads()` |
| `bra` | 分支跳转 |
| `@%p0` | 谓词寄存器，条件执行 |

### 实际用法

你不需要手写 PTX。但在以下场景阅读 PTX 很有用：
- **确认循环是否被展开**：找 `bra` 指令数
- **看有无不必要的 global 访存**：数 `ld.global` 和 `st.global`
- **看寄存器用量**：头部 `.reg` 声明数量
- **确认 FMA 是否被编译器识别**：应该看到 `fma` 而不是 `mul + add`

---

## 头文件组织

实际项目中 CUDA 代码常见组织方式：

```
project/
├── CMakeLists.txt
├── include/
│   ├── common.h          # host/device 通用宏和函数
│   └── cuda_utils.cuh    # CUDA 专用工具（可以是 .cuh 或 .h）
├── src/
│   ├── main.cpp
│   └── kernels/
│       ├── gemm.cu
│       └── reduce.cu
```

`.cuh` 约定：包含 `__global__` / `__device__` 函数声明的头文件。
`.h` 约定：纯 host 代码或 `__host__ __device__` 双端函数。

```cuda
// cuda_utils.cuh
#pragma once
#include <cuda_runtime.h>
#include <cstdio>

#define CUDA_CHECK(call) /* ... */  // 之前定义的错误检查宏

// 计算 grid 维度的小工具（几乎每个项目都要用）
inline dim3 grid_dims(int n, int block_size) {
    return dim3((n + block_size - 1) / block_size);
}

// __host__ __device__ 函数：可被 host 和 device 同时调用
inline __host__ __device__ int ceiling_div(int a, int b) {
    return (a + b - 1) / b;
}
```

---

## 编译期 vs 运行期

一个容易被忽略但很重要的区分：

```cuda
// 编译期确定（模板参数 / constexpr）
template <int BLOCK_SIZE>
__global__ void kernel(...) { ... }
kernel<256><<<grid, 256>>>(...);  // BLOCK_SIZE 是编译期常量

// 运行期确定
void launch_kernel(int block_size) {
    kernel<<<grid, block_size>>>(...);  // block_size 是运行期变量，但 <<<>>> 内也接受
}
```

编译期常量可以触发编译器优化（循环展开等）。运行期变量不行。

---

## 关键生存技能总结

1. **能把项目编译起来**：看懂 CMake 里的 `CMAKE_CUDA_ARCHITECTURES`、`CMAKE_CUDA_FLAGS`，知道怎么加 `-arch=sm_xx`
2. **能看懂编译报错**：`calling __host__ from __global__` = 函数类型不匹配；`unresolved extern` = 缺定义或没开 separable compilation
3. **能查寄存器用量**：`nvcc --ptxas-options=-v` 看编译器输出
4. **能用 compute-sanitizer**：定位越界访问
5. **能读基本的 PTX**：确认 FMA、loop unroll、global load/store 模式

---

## 下一篇文章

第四篇讲常见错误排查与调试工具链：compute-sanitizer 实战、cuda-gdb 基础用法、Nsight Systems 初步 profiling，以及最常见 10 个 CUDA 错误的诊断和修复。
