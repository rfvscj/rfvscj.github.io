---
title: f1-score
date: 2023-08-03 21:12:32
categories: 零碎笔记
tags: []
---

### f1-Score
$f1=2*\frac{p*r}{p+r}$
#### precision
即准确率

#### recall
即召回率
### micro-F1
**取值范围**：(0, 1)；  
**权重倾向**：每一个样本的权重都相同；  
**适用环境**：多分类不平衡，若数据极度不平衡会影响结果；
**计算方式**：计算总的召回率和总的准确率然后算

### macro-F1
**取值范围**：(0, 1)；  
**取值范围**：每一类别的权重都相同；  
**适用环境**：多分类问题，不受数据不平衡影响，容易受到识别性高（高recall、高precision）的类别影响；
**计算方式**：计算每个类别的F1-score，然后求平均