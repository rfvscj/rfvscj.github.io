---
title: 自定义loss
tags: []
categories:
  - 零碎笔记
date: 2023-02-27 19:19:05
---

按照神经网络的形式计算即可
```
class My_loss(nn.Module):
    def __init__(self):
        super().__init__()
        
    def forward(self, x, y):
        return torch.mean(torch.pow((x - y), 2))
```

