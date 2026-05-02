---
title: f1-score
categories:
  - CV必备
tags: []
date: 2023-08-03 21:12:32
index_img: /img/bg4.png
excerpt: F1-score 用来同时看 precision 和 recall，尤其适合类别不平衡、只看 accuracy 会误导你的分类任务。
---

F1-score 是分类任务里非常常见的评价指标，尤其适合“只看准确率会误导你”的场景。

## 为什么不能只看 Accuracy

举个极端例子：如果一个二分类数据集里，负类占 95%，正类只占 5%。模型无脑把所有样本都预测成负类，也能拿到 95% 的 accuracy。这显然不代表模型真的有用。

很多时候我们更关心：

- 预测为正的样本里，到底有多少是真的
- 真实为正的样本里，到底抓到了多少

这就对应了 precision 和 recall。

## Precision 和 Recall

### Precision

精确率，表示预测为正的样本里，有多少是真的正样本。

$$
precision = \frac{TP}{TP + FP}
$$

如果 precision 很低，说明模型“喜欢乱报”。

### Recall

召回率，表示所有真实正样本里，有多少被模型找出来了。

$$
recall = \frac{TP}{TP + FN}
$$

如果 recall 很低，说明模型漏掉了很多真正重要的样本。

## F1-score

F1 是 precision 和 recall 的调和平均：

$$
F1 = 2 \cdot \frac{precision \cdot recall}{precision + recall}
$$

之所以不用普通平均，而用调和平均，是因为它会惩罚“一个很高、一个很低”的情况。

## micro-F1

**取值范围**：`(0, 1)`  
**权重倾向**：每个样本权重相同  
**计算方式**：先把所有类别的 TP、FP、FN 汇总，再统一计算 precision、recall 和 F1

它更像在问：整个数据集上，模型总体表现如何？

## macro-F1

**取值范围**：`(0, 1)`  
**权重倾向**：每个类别权重相同  
**计算方式**：先分别算每个类别的 F1，再对各类别取平均

它更像在问：模型对每个类别是不是都还算公平？

## 什么时候看哪个

- 如果你关心整体分类效果，可以看 `micro-F1`
- 如果你关心少数类、不平衡数据，通常要重点看 `macro-F1`
- 如果是二分类问题，还要结合 precision-recall tradeoff 一起看

## 总结

F1-score 的价值在于，它把 precision 和 recall 绑在一起看，避免模型靠“乱报”或“少报”取得虚假的高分。二分类里先理解 precision、recall、F1 的关系；多分类里再分清 `micro-F1` 和 `macro-F1`，基本就够用了。
