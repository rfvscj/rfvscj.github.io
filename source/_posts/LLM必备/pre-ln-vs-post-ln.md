---
title: Pre-LN vs Post-LN：Transformer 中 LayerNorm 的位置
categories:
  - LLM必备
tags:
  - LayerNorm
  - Transformer
  - 训练稳定性
  - 深度学习
date: 2026-05-15 12:00:00
updated: 2026-05-15 12:00:00
index_img: /img/bg4.png
excerpt: Pre-LN 和 Post-LN 决定了 Transformer 训练的稳定性和收敛速度。本文从梯度流出发讲清楚为什么现代大模型都用 Pre-LN，附带 PyTorch 实现对比。
---

LayerNorm 放哪？这个看似微小的设计决策，决定了 Transformer 能否在数百层下稳定训练。

## 两种架构

```
Post-LN (原始 Transformer, 2017):
  x → Attention(x) → + → LN → FFN → + → LN → output

Pre-LN (现代大模型主流):
  x → LN → Attention(x) → + → LN → FFN → + → output
```

差异就两行代码的位置交换，但训练行为天差地别。

## 数学形式

一个 Transformer 层的通用形式：

$$x_{k+1} = x_k + f_k(x_k)$$

其中 $f_k$ 是 attention 或 FFN 子层。

### Post-LN

$$x_{k+1} = \text{LN}\big(x_k + f_k(x_k)\big)$$

LayerNorm 在残差加完之后。**每一层的输出都被归一化**，再送入下一层。

### Pre-LN

$$x_{k+1} = x_k + f_k\big(\text{LN}(x_k)\big)$$

LayerNorm 在子层之前。残差连接**绕过 LayerNorm**，输出不归一化。

## 为什么 Pre-LN 更稳定

核心在于**梯度的传播路径**不同。

### Post-LN 的梯度问题

对于一个 L 层的 Post-LN Transformer，输入 $x_0$ 对 loss 的梯度：

$$\frac{\partial \mathcal{L}}{\partial x_0} = \frac{\partial \mathcal{L}}{\partial x_L} \cdot \prod_{k=L-1}^{0} \frac{\partial x_{k+1}}{\partial x_k}$$

其中每一项包含 LayerNorm 的梯度。LayerNorm 的梯度中有 $\frac{1}{\sigma}$ 项（$\sigma$ 是输入的 std），当 $\sigma$ 较大时梯度被压缩。L 层连乘下来，梯度指数级衰减——**梯度消失**。

更深层的问题：Post-LN 下残差分支的输出方差随层数增长，导致 LayerNorm 的输入方差逐层放大，训练前期极易发散。这就是原始 Transformer 需要 **warmup** 的根本原因。

### Pre-LN 的梯度优势

Pre-LN 下，残差连接形成一条从输出直达输入的"高速公路"：

$$x_L = x_0 + \sum_{k=0}^{L-1} f_k\big(\text{LN}(x_k)\big)$$

梯度：

$$\frac{\partial \mathcal{L}}{\partial x_0} = \frac{\partial \mathcal{L}}{\partial x_L}\left(1 + \sum_{k} \frac{\partial}{\partial x_0} f_k(\text{LN}(x_k))\right)$$

那个 **1** 是关键——它来自残差连接的恒等映射，保证了梯度至少有一条无损的传播路径。不会指数衰减。

更直观地说：**Pre-LN 下，残差分支的输出按 $\sqrt{L}$ 增长（而不是指数增长），LayerNorm 的输入方差始终可控。**

## PyTorch 实现对比

```python
import torch
import torch.nn as nn

# ========== Post-LN ==========
class PostLNTransformerBlock(nn.Module):
    def __init__(self, d_model, d_ff, num_heads):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, num_heads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
        )
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)

    def forward(self, x):
        # LN 在残差之后
        x = self.ln1(x + self.attn(x, x, x, need_weights=False)[0])
        x = self.ln2(x + self.ffn(x))
        return x

# ========== Pre-LN ==========
class PreLNTransformerBlock(nn.Module):
    def __init__(self, d_model, d_ff, num_heads):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, num_heads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
        )
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)

    def forward(self, x):
        # LN 在子层之前，残差绕过 LN
        x = x + self.attn(self.ln1(x), self.ln1(x), self.ln1(x),
                          need_weights=False)[0]
        x = x + self.ffn(self.ln2(x))
        return x
```

注意 Pre-LN 里 `self.ln1(x)` 传了三次——因为 MHA 的 Q、K、V 都从同一个 x 投影。

## 训练行为对比

| | Post-LN | Pre-LN |
|---|---|---|
| 梯度流 | 随深度指数衰减 | 恒等通路保底，不衰减 |
| 训练初期 | 极易发散，必须 warmup | 不需要 warmup |
| 最终性能（浅层 < 12L） | 略好 | 略差或持平 |
| 最终性能（深层 > 24L） | 难以训练 | 显著更优 |
| 残差输出方差 | 逐层放大 | $\sqrt{L}$ 增长，可控 |
| 主流使用 | 原始 Transformer、BERT-base | GPT-2/3/4、LLaMA、大多数现代 LLM |

**一条实用的经验线**：12 层以下 Post-LN 可能更好；超过 24 层 Pre-LN 几乎是必须的。LLaMA-65B 有 80 层，如果用 Post-LN，warmup 阶段可能都过不去。

## 变体：Sandwich-LN 和 DeepNorm

### Sandwich-LN

在 Pre-LN 基础上，残差分支前后各加一个 LN（但残差仍绕过一个）：

这实际上是很多视觉 Transformer（ViT）的默认做法，在多层感知机场景下比纯 Pre-LN 略稳定。

### DeepNorm (Microsoft, 2022)

$$\text{DeepNorm}(x) = \text{LN}(\alpha \cdot x + f(x))$$

在 Post-LN 的位置，但残差分支乘了一个小于 1 的缩放因子 $\alpha$，且初始化时做了特殊处理。结果：**1000 层 Post-LN 也能稳定训练**。

但对大多数场景来说，Pre-LN 已经够用。DeepNorm 主要是给"我们就是要用 Post-LN 并且要极深"的场景准备的。

## RMSNorm：LayerNorm 的轻量替代

现代 LLM（LLaMA 系列）用的不是标准 LayerNorm，而是 **RMSNorm**：

```python
class RMSNorm(nn.Module):
    def __init__(self, d_model, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d_model))
        self.eps = eps

    def forward(self, x):
        # 只除 RMS，不去均值
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + self.eps)
        return x / rms * self.weight
```

$$ \text{RMSNorm}(x) = \frac{x}{\sqrt{\frac{1}{d}\sum x_i^2 + \epsilon}} \cdot \gamma $$

和 LayerNorm 的区别：**不做去均值（re-centering），只做缩放（re-scaling）**。省了一次 reduce 操作，在模型很大时有可感知的加速。

LLaMA 的做法：**Pre-RMSNorm**——RMSNorm 放在子层之前，架构和 Pre-LN 相同，只是把 LayerNorm 换成 RMSNorm。

## 工程建议

1. **新项目默认用 Pre-LN**。不需要 warmup，不需要调 LayerNorm 位置相关的超参。
2. **12 层及以下的小模型**，Post-LN 可能让收敛略快一点，但差距不大。如果已经在用 Pre-LN 就继续用。
3. **配合 RMSNorm**。如果模型很大（>1B 参数），把 LayerNorm 换成 RMSNorm 不改变训练行为，但有 5-10% 的 forward 加速。
4. **不需要 warmup 不意味着不需要 learning rate schedule**。余弦退火或线性衰减仍然是收敛良好的必要组件。
5. **检查已有代码的 LN 位置**。很多老模型（BERT-base 的 HuggingFace 实现）用的是 Post-LN。如果要改 Pre-LN，注意这不只是换代码，需要重新训练——Pre-LN 和 Post-LN 的 loss landscape 完全不同，权重不能通用。
