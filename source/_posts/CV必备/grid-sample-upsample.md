---
title: 智驾感知中的采样：grid_sample 与 upsample 原理与用法
categories:
  - CV必备
tags:
  - 智驾感知
  - BEV
  - grid_sample
  - upsample
  - 采样算法
date: 2026-05-14 12:00:00
updated: 2026-05-14 12:00:00
index_img: /img/bg4.png
excerpt: 梳理智驾感知模型中 grid_sample、upsample 及其它关键采样操作的数学原理、PyTorch 用法和设计取舍。
---

智驾感知模型大量依赖空间采样操作：从透视特征转到 BEV、从低分辨率回到高分辨率、从特征图中按不规则位置取点。这篇文章系统梳理 `grid_sample`、`upsample` 及其它常见采样算法的原理和用法。

## grid_sample：按坐标采样

`torch.nn.functional.grid_sample` 是最灵活的空间采样算子：给定一个输入特征图和一组采样坐标，它从指定位置插值出值来。

### 函数签名

```python
F.grid_sample(
    input,          # (N, C, H_in, W_in)
    grid,           # (N, H_out, W_out, 2)
    mode='bilinear',     # 'bilinear' | 'nearest' | 'bicubic'
    padding_mode='zeros',# 'zeros' | 'border' | 'reflection'
    align_corners=False,
)
```

- `grid` 的值域为 `[-1, 1]`，`(-1, -1)` 对应图像左上角，`(1, 1)` 对应右下角
- `align_corners=True` 时角点像素中心对齐，`False` 时像素边界对齐（PyTorch 默认 `False` 更接近图像处理的约定）
- 输出在 `(h_out, w_out)` 位置的值 = 对 `input` 在 `grid[n, h, w, :]` 坐标处做双线性插值

### 最简单的例子：输入输出长什么样

用一张 4×4 的图像，按规则格点采样看效果：

```python
import torch
import torch.nn.functional as F

# 输入: 单通道 4×4 特征图
# 值从 0 递增到 15 方便观察采样位置
input = torch.arange(16., dtype=torch.float32).reshape(1, 1, 4, 4)
print("输入 (1, C, H, W):")
print(input[0, 0])
# tensor([[ 0.,  1.,  2.,  3.],
#         [ 4.,  5.,  6.,  7.],
#         [ 8.,  9., 10., 11.],
#         [12., 13., 14., 15.]])

# grid: (1, 2, 2, 2)，最后维是 (x, y)
# 想做 2×2 的输出，从中采样 4 个点
# 左上角 (-1,-1) → 采样 input 左上角 → 值接近 0
# 右下角 ( 1, 1) → 采样 input 右下角 → 值接近 15
grid = torch.tensor([
    [-1., -1.],   # 左上
    [ 1., -1.],   # 右上
    [-1.,  1.],   # 左下
    [ 1.,  1.],   # 右下
]).reshape(1, 2, 2, 2)  # (N, H_out, W_out, 2)

out = F.grid_sample(input, grid, mode='bilinear', align_corners=False)
print("输出 (1, 1, 2, 2):")
print(out[0, 0])
# align_corners=False 下 (-1,-1) 对应第一条边外侧一半的位置
# align_corners=True 下 (-1,-1) 精确对应第 0 个像素中心

# 更直观的例子：从 4×4 中按指定坐标采样
# 构造一个标量坐标手动验证
def sample_one(x, y):
    """从 input 的 (x,y) 位置采样，返回双线性插值结果"""
    g = torch.tensor([[[[x, y]]]])  # (1, 1, 1, 2)
    return F.grid_sample(input, g, align_corners=True).item()

print(f"采样 (0, 0): {sample_one(-1, -1):.1f}")   # 左上角 → ~0
print(f"采样 (1, 0): {sample_one( 1, -1):.1f}")   # 右上角 → ~3
print(f"采样 (0, 1): {sample_one(-1,  1):.1f}")   # 左下角 → ~12
print(f"采样中心:   {sample_one( 0,  0):.1f}")     # 正中心 → ~7.5 (四邻域的均值)
```

**核心理解**：输入 `(N, C, H_in, W_in)` + grid `(N, H_out, W_out, 2)` → 输出 `(N, C, H_out, W_out)`。grid 的最后一维 `(x, y)` 告诉算子"从输入的哪个位置拿值"，输出尺寸完全由 grid 的 `(H_out, W_out)` 决定。

### 双线性插值的数学过程

对于任意浮点坐标 `(x, y)`（在 `grid` 中由归一化坐标映射回实际像素坐标后），双线性插值分两步：

**第一步：找到四个最近邻像素**

记 `(x, y)` 的四个整数邻域为：

- `(x1, y1)` = `(floor(x), floor(y))`
- `(x1, y2)` = `(floor(x), floor(y) + 1)`
- `(x2, y1)` = `(floor(x) + 1, floor(y))`
- `(x2, y2)` = `(floor(x) + 1, floor(y) + 1)`

**第二步：按距离做加权平均**

$$
\begin{aligned}
f(x,y) &= f(x_1,y_1) \cdot (x_2 - x)(y_2 - y) \\
       &+ f(x_2,y_1) \cdot (x - x_1)(y_2 - y) \\
       &+ f(x_1,y_2) \cdot (x_2 - x)(y - y_1) \\
       &+ f(x_2,y_2) \cdot (x - x_1)(y - y_1)
\end{aligned}
$$

插值核是可微的（分段线性），所以梯度可以回传到输入特征图和采样坐标。

### 在 BEV 感知中的核心用法：LSS / BEVDet 的视锥投影

grid_sample 在 BEV 模型中最关键的用处是 **透视特征到 BEV 的变换**。以 LSS（Lift-Splat-Shoot）和 BEVDet 为代表，整体流程是：

1. **Lift**：对图像特征每个像素预测深度分布，生成图像视锥特征（尺寸 `(N, C, D, H, W)` 或 point-based 表示）
2. **Splat**：用相机内外参将视锥中每个点的 3D 坐标投影到 BEV 网格坐标
3. **采样**：用 grid_sample 从 BEV 坐标反查图像特征，填入 BEV 特征图

其中第 3 步的具体做法（以 BEVDet 为例）：

```python
# frustum_coords: (B, D, H, W, 3) — 视锥中每个点在世界/自车坐标系的 (x, y, z)
# bev_grid: (B, H_bev, W_bev, 2) — BEV 特征图上每个像素对应的采样坐标

# 将 3D 视锥坐标映射到 BEV 网格
# 取 x, y 分量，归一化到 [-1, 1]
bev_x = (frustum_coords[..., 0] - x_min) / (x_max - x_min) * 2 - 1
bev_y = (frustum_coords[..., 1] - y_min) / (y_max - y_min) * 2 - 1
sampling_grid = torch.stack([bev_x, bev_y], dim=-1)  # 注意 grid_sample 需要的顺序是 (x, y)

# 从高分辨率图像特征采样到 BEV
bev_feat = F.grid_sample(image_feat, sampling_grid, mode='bilinear', align_corners=False)
# image_feat: (B, C, H_img, W_img)
# sampling_grid: (B, H_bev, W_bev, 2)
# output bev_feat: (B, C, H_bev, W_bev)
```

> **注意顺序**：`grid_sample` 的 grid 通道顺序是 `(x, y)` 即 `(宽方向, 高方向)`，和 NumPy/image 的 `(y, x)` 习惯相反。这是最常见的踩坑点。

### grid_sample 的优缺点

| 优点 | 缺点 |
|---|---|
| 完全可微，梯度可回传到特征和坐标 | 计算量随输出分辨率线性增长 |
| 坐标可以是动态计算的结果 | 双线性插值的感受野有限（只有 4 邻域） |
| 适用于任意几何变换 | nearest 模式下有离散化误差 |
| 天然支持 batch 操作 | 归一化坐标容易写出 off-by-one 的 bug |

### 与 scatter / indexing 的对比

一些 BEV 实现（如纯 LSS 原始实现）用 scatter 操作把视锥点索引到 BEV 格子：

```python
# scatter 方式：每个 3D 点直接写入对应的 BEV 索引
bev_feat = torch.zeros(B, C, H_bev, W_bev)
bev_feat.scatter_add_(dim, index, src)
```

对比：

- **scatter** 是离散写入，每个点落在一个固定格子里，没有梯度跨格传播
- **grid_sample** 是连续插值，值会影响周围格子，梯度可以传播到坐标
- scatter 更快但不可微；grid_sample 可微但更慢
- 工程上常用 scatter 做特征聚合（已经不需要梯度到坐标的场景）

## upsample：上采样全家桶

上采样在感知模型中无处不在：FPN 自顶向下路径、分割头、深度估计解码器。PyTorch 中主要有四种方式。

### 1. F.interpolate（插值上采样）

最直接的上采样方式，不引入额外参数。

```python
F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)
F.interpolate(x, size=(64, 64), mode='nearest')
```

模式选择：

| mode | 适用场景 |
|---|---|
| `nearest` | 标签 / mask 上采样，避免引入非整数值 |
| `bilinear` | 特征图上采样，最常用 |
| `bicubic` | 需要更平滑的上采样结果 |
| `trilinear` | 3D 特征（如 CT 体积）上采样 |

`align_corners` 的影响（bilinear/bicubic 下）：

- `True`：角点像素中心对齐，适合输入输出尺寸刚好倍数关系且需要精确保留边界的场景
- `False`（默认）：像素边界对齐，坐标映射更一致，**通常推荐默认值**

### 最简单的例子：输入输出长什么样

```python
import torch
import torch.nn.functional as F

# 输入: 2 通道的 2×2 特征图
x = torch.tensor([[[[1., 2.],
                    [3., 4.]],
                   [[5., 6.],
                    [7., 8.]]]])
print("输入 shape:", x.shape)  # (1, 2, 2, 2)

# --- F.interpolate: 无参数上采样 ---
out = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)
print("interpolate 输出 shape:", out.shape)  # (1, 2, 4, 4)

# --- nn.Upsample: 等效于上一行，可放入 nn.Sequential ---
upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
print("Upsample 输出 shape:", upsample(x).shape)  # (1, 2, 4, 4)

# --- 转置卷积: 带参数上采样 ---
deconv = nn.ConvTranspose2d(2, 2, kernel_size=4, stride=2, padding=1)
print("ConvTranspose2d 输出 shape:", deconv(x).shape)  # (1, 2, 4, 4)

# --- PixelShuffle: 通道换空间 ---
# 输入需要 r² 倍通道数，r 为上采样倍数
x4c = torch.randn(1, 8, 2, 2)  # 8 = 2 * 2²（目标通道 2 × 上采样 2²）
shuffle = nn.PixelShuffle(upscale_factor=2)
print("PixelShuffle 输出 shape:", shuffle(x4c).shape)  # (1, 2, 4, 4)
```

**核心理解**：

| 操作 | 输入 shape | 输出 shape | 有无参数 |
|---|---|---|---|
| `F.interpolate` | `(1, 2, 2, 2)` | `(1, 2, 4, 4)` | 无 |
| `nn.Upsample` | `(1, 2, 2, 2)` | `(1, 2, 4, 4)` | 无 |
| `ConvTranspose2d` | `(1, 2, 2, 2)` | `(1, 2, 4, 4)` | 有（可学习卷积核） |
| `PixelShuffle` | `(1, 8, 2, 2)` | `(1, 2, 4, 4)` | 无（只做重排） |

关键知识点：`F.interpolate` 的上采样本质上是先构造目标网格坐标，再做采样——和 `grid_sample` 是同一套底层机制。`align_corners=True` 和 `False` 的差异直接对应 grid_sample 的坐标生成逻辑不同。

```python
# F.interpolate(scale_factor=2) 等效于:
# 1. 生成目标尺寸下的归一化坐标网格
# 2. 用 grid_sample 做双线性采样
```

### 2. 转置卷积（ConvTranspose2d）

带参数的上采样，可以学习上采样模式，但对超参数敏感。

```python
nn.ConvTranspose2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1)
```

内部原理：对输入特征图做插零扩展，再卷积：

1. 在输入像素之间插入 `stride - 1` 个零
2. 补 `kernel_size - 1 - padding` 圈零的 padding
3. 做普通卷积

**棋盘效应（checkerboard artifacts）**：当 `kernel_size` 不能被 `stride` 整除时，输出上会出现周期性亮度不均的格子状伪影。原因是插零后不同位置的像素参与卷积的次数不同。

避免棋盘效应的规则：
- `kernel_size` 设为 `stride` 的整数倍（常用 `kernel_size=4, stride=2`）
- 或者使用 `F.interpolate + Conv2d` 的组合替代

```python
# 推荐替代方案：插值 + 卷积，无棋盘效应
class UpsampleConv(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()
        self.upsample = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False)
        self.conv = nn.Conv2d(in_c, out_c, 3, padding=1)

    def forward(self, x):
        return self.conv(self.upsample(x))
```

### 3. Pixel Shuffle（亚像素卷积）

一种精巧的上采样方式：用通道换空间分辨率。

```python
nn.PixelShuffle(upscale_factor=2)  # 输入 C*r^2 通道 → 输出 C 通道，分辨率 ×r
```

原理：把 `(C × r², H, W)` 的输入重新排列成 `(C, H × r, W × r)` 的输出。

```
输入: [A1, B1, C1, D1,  A2, B2, C2, D2,  A3, B3, C3, D3,  A4, B4, C4, D4] (16通道, H, W)
输出: 4通道, 2H, 2W

输出像素排列:
  A1 B1    A2 B2
  C1 D1    C2 D2

  A3 B3    A3 B4     ← 每个位置的像素来自不同通道
  C3 D3    C4 D4
```

优势：
- **计算量低**：没有卷积中的填充和零扩展开销
- **参数量少**：通常 pixel shuffle 前只放一个 1×1 conv 做通道升维
- **无棋盘效应**：不会引入不均匀的采样

在 SRCNN 系列（超分）和 YOLO 检测头中广泛使用。

### 4. 四种上采样对比

| 方法 | 参数量 | 计算量 | 灵活性 | 常见用途 |
|---|---|---|---|---|
| `F.interpolate` | 0 | 低 | 固定插值模式 | 临时上采样、FPN 上采样 |
| `interpolate + Conv` | 少量 | 中 | 可学习 | 分割头、深度解码器 |
| `ConvTranspose2d` | 较多 | 高 | 完全可学习 | 生成模型、VAE decoder |
| `PixelShuffle` | 少量 | 低 | 高效 | 超分、高效检测头 |

### 实际工程建议

- **FPN 上采样**：用 `F.interpolate(bilinear)` 就够了，不需要加参数
- **分割 / 深度解码器**：用 `Upsample(bilinear) + Conv2d`，比转置卷积稳定
- **计算资源紧张时**：用 `PixelShuffle` 替代转置卷积
- **标签图**：必须用 `nearest`，避免引入浮点数标签值
- **多尺度输出需要严格对齐时**：注意 `align_corners` 的一致性，前后不一致会导致特征不对齐

## 其他重要的采样算法

### Deformable Convolution（可变形卷积）

DCN 让卷积核的采样位置不再是固定格点，而是学习一组偏移量。

```python
# DCNv2 的核心思想（简化版）
offset = offset_conv(x)       # 学习每个位置的采样偏移
modulation = modulation_conv(x)  # 学习每个采样点的权重
x_deform = deform_conv2d(x, offset, modulation)
```

**为什么重要**：智驾场景中目标尺度变化大、形状不规则，固定格点的卷积核无法自适应。DCN 让感受野"变形"以贴合目标形状。BEVFormer 和很多现代 BEV 检测头都用 DCN 做 temporal/spatial cross-attention。

### RoIAlign

两阶段检测器（如 Mask R-CNN）中，从 feature map 提取不规则 ROI 特征的标准操作。

```python
roi_features = roi_align(feature_map, rois, output_size=(7, 7), spatial_scale=1/16)
```

相比 RoIPool 的两次量化（边界量化 + 格点量化），RoIAlign 用双线性插值消除量化误差，对小目标检测精度提升显著。本质上是 `grid_sample` 的 ROI 特化版。

### LiDAR 点云的体素采样

激光雷达点云需要在进入网络前做结构化处理：

**硬体素化（hard voxelization）**：每个体素格内随机采样固定数量点，超过的丢弃，不足的补零。VoxelNet / PointPillars 的经典做法。

**软体素化 / 动态体素化**：不限制每格点数，用 scatter 或稀疏卷积处理变长数据，保留更多信息。

**柱体采样（Pillar Sampling）**：PointPillars 的做法——z 方向不切分，只做 x-y 平面柱体化，用 PointNet 提取柱内特征后投影到 BEV。

```python
# PointPillars 风格的柱体化伪代码
pillar_indices = (points[:, :2] - min_xy) / pillar_size  # x, y → pillar index
pillar_feats = scatter_max(point_feats, pillar_indices)   # 每柱 max pooling
bev_feat = pillar_feats.reshape(B, C, H_bev, W_bev)       # 展成 BEV 图
```

### 多尺度特征采样

FPN 多尺度融合时需要从不同分辨率的特征图采样：

```python
# 典型的 FPN 自顶向下流程
p5_up = F.interpolate(p5, scale_factor=2, mode='bilinear')
p4_out = p4_conv(p4 + p5_up)
```

BiFPN（EfficientDet）和 PANet 在此基础上加了更多跨尺度连接，但采样操作的核心仍然是 `interpolate` 和 pooling。

## 总结

- 需要**按不规则坐标采样**：用 `grid_sample`，典型的 BEV 投影和几何变换场景
- 需要**上采样特征图**：优先用 `F.interpolate(bilinear)` 或 `interpolate + Conv2d`，避免转置卷积的棋盘效应
- 需要**高效超分或检测头**：用 `PixelShuffle`
- 需要**自适应感受野**：用可变形卷积
- 需要**ROI 池化**：用 `RoIAlign`（本质是 grid_sample 的规整化版本）
- LiDAR 点云：按检测器类型选用体素采样或柱体采样
- 多尺度融合：`interpolate` 配合加和或 concat

这些采样操作构成了感知模型的"空间推理层"——几乎所有从一种表示转到另一种表示的操作，本质上都是在做某种形式的坐标映射 + 插值采样。理解了这些，看任何 BEV 或检测模型的架构图都能快速拆解出它在哪一步用了哪种采样。
