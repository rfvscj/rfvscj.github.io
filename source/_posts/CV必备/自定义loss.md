---
title: 自定义loss
tags: []
categories:
  - CV必备
date: 2023-02-27 19:19:05
index_img: /img/bg1.png
excerpt: 自定义 loss 的关键不是会不会写 PyTorch 模块，而是你能否把真正想优化的目标写成稳定、可微的训练信号。
---

自定义 loss 的本质，就是把你真正想优化的目标写成一个可微分、能参与反向传播的函数。

很多时候，框架自带的 `CrossEntropyLoss`、`MSELoss`、`BCEWithLogitsLoss` 已经够用；但如果任务有额外约束，或者你想把多个目标揉在一起优化，就需要自己写 loss。

## 一个最小例子

下面这个例子本质上就是手写版 MSE：

```python
class My_loss(nn.Module):
    def __init__(self):
        super().__init__()
        
    def forward(self, x, y):
        return torch.mean(torch.pow((x - y), 2))
```

这里做的事情很简单：

- `x` 是预测值
- `y` 是目标值
- 先求差
- 再平方
- 最后对所有元素取平均

## 自定义 loss 的常见场景

### 1. 多个目标一起优化

例如目标检测里，可能同时有：

- 分类损失
- 边框回归损失
- 正则项

最终 loss 往往是它们的加权和。

### 2. 加入任务特定约束

有些任务不仅要求预测准，还要求：

- 排序关系正确
- 正负样本间有 margin
- 输出满足某种结构约束

这种时候就需要自己定义更贴近任务目标的损失。

### 3. 改善类别不平衡或样本难度问题

例如 focal loss、class-balanced loss，本质上都是在标准 loss 上做修改。

## 写自定义 loss 时要注意什么

### 可微

如果你的 loss 里用了不可导、或者梯度几乎传不回去的操作，那么模型可能根本学不动。

### 标量输出

大多数训练循环默认希望 loss 最终是一个标量。如果你返回的是一个向量，通常还需要再做一次 `mean()` 或 `sum()`。

### 数值稳定性

手写 `log`、`exp`、除法时要特别小心。很多框架自带 loss 会把数值稳定性处理掉，自己写时这部分责任就落到你头上了。

### 权重尺度

如果你把多个 loss 直接相加，但它们量级差很多，那么训练会被其中一项主导。这时候通常需要加权。

## 一个稍微实用一点的写法

```python
class WeightedMSELoss(nn.Module):
    def __init__(self, alpha=1.0):
        super().__init__()
        self.alpha = alpha

    def forward(self, pred, target):
        mse = torch.mean((pred - target) ** 2)
        reg = torch.mean(torch.abs(pred))
        return mse + self.alpha * reg
```

## 调试建议

自定义 loss 写完以后，至少要检查三件事：

- loss 数值是不是正常，不是一上来就 `nan`
- 反向传播能不能跑通
- loss 下降时，模型指标是否真的变好

## 总结

自定义 loss 不难，难的是把“我真正想让模型学什么”写清楚。写法层面只是 PyTorch 模块；真正有技术含量的部分，是目标怎么拆、权重怎么定、梯度是否稳定，以及 loss 的下降是否真的代表任务变好。
