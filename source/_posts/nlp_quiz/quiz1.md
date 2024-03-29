---
title: quiz1
tags: []
categories:
  - nlp_quiz
date: 2023-09-19 10:25:55
---

## NLP quiz 1

### tuple和list的区别
list可变，tuple不可变。
这里有个知识点是，对不可变对象的赋值如何进行。
### micro F1和macro F1的区别
#### FN，TN，FP，TP
F和T修饰的是后边的PN，即，FN是实际上正样本，被错误识别成了负样本
#### macroF1
分别对每个类别按照二分类，计算一个对应的F1，然后取平均即可。
数据不平衡时效果较好，**对稀有类别更好。**

#### microF1
不区分类别，计算整体的F1
1. 对每个类别，分别计算对应的FP，TP，FN，TN

### 介绍GBDT
#### Boosting
基学习器间串行，有依赖
#### Bagging
基学习器间并行，无依赖

Gradient Boosting Decision Tree，梯度提升决策树，是Boosting算法
构造一组弱的学习器（树），多棵决策树结果**累加**（不平均）作为最终输出。
每一次计算前一个学习器的残差。
适用于稠密数据和数值型特征，NLP表现不好

### 为什么用交叉熵不用MAE
1. 有效惩罚错误样本，因为有指数，偏差大了损失会很大
2. 推动模型更快地收敛

### RNN的缺陷
#### 梯度消失
因为sigmoid导数小于零，所以多级下去，会导致梯度越来越小，导致梯度消失
#### 对所有输入相同对待
没有区分那些信息可以是无用的，每次进来一个输入，都无区别的进行计算

### 介绍子词分词和BPE
#### 子词分词
就是把词分得更细，一定程度上解决OOV问题
#### BPE 
Byte Pair Encoding，字节对编码
先将词分为单个字符，然后用另一个字符替换频率最高的**一对**字符，如此循环直到结束（设定期望量）
每次频率最高的字符对，merge，而且可参与后续的merge
最后剩余的替换为\<unk>
一般中文不需要BPE，英文需要，bert词表里的##就是

### 不同词向量的区别
#### 相同
都是分布式语义，词义取决于上下文
#### Word2Vec
- CBOW 用周围词预测当前词
- Skip-gram 用当前词预测周围词

不能处理OOV词
#### FastText
- 输入层 输入为Embedding后的单词和ngram表征
- 隐藏层 多个词向量平均
- 输出层 文档类别标签，分层softmax
词向量怎么训的，暂且不知道
能应对OOV

#### BERT
动态表征

### Attention的时间复杂度
#### 矩阵乘法复杂度
$n*m$和$m*n$的矩阵相乘，复杂度是$O(n^2m)$
**但是务必注意，三个矩阵相乘，本质上是先两两乘，再两两乘，是先后的操作，只是计算量翻了一倍，而不是复杂度等级提升。**
#### 缩放点积注意力复杂度
$$Attention=Softmax(\frac{QK^T}{\sqrt{D_K}})V$$
QK相乘，$O(n^3)$，softmax， $O(n)$，中间结果再乘V，$O(n^3)$，整体复杂度是$O(n^3)$
### 为什么Attention除以$\sqrt{D_k}$
1. 首先要除以一个数，是为了让softmax的值不太大，否则由于指数的特性，偏导容易趋于零
2. 为什么除以$\sqrt{D_K}$，是为了控制方差为1不变
### BERT的结构
- 位置编码是可学习的
- 用的GELU激活函数
- 先加，再norm
- attention后边还有一个dense层
#### google实现
layer_norm加在了attention_output与前一层的残差连接后和attention_output与ffn的残差连接处
#### HuggingFace实现
和google的实现好像是一样的，需要注意attetion和ffn之间还有个dense层，然后 add&norm，接入ffn，又是一个ffn
#### Annotated Transformer Encoder
- 位置编码是sin/cos函数计算出来的固定值
- 先norm，然后通过attention/ffn，然后和未norm的残差连接
- 比bert少一个attention后的dense层
- 用的ReLU

### GPT-1，2，3，3.5的区别
模型结构
![](../../images/Pasted%20image%2020230920105631.png)
#### GPT-1
参数量1.17亿，和bert相当
无监督后又有监督地微调
#### GPT-2
参数量15亿，即1.5B
去掉了有监督

#### GPT-3
2020年
参数量1750亿，175B
#### GPT-3.5
一系列大模型，如text-davinci-00x，gpt-3.5-turbo，
包括InstructGPT
其中gpt-3.5-turbo就是ChatGPT
#### InstructGPT
- 指令微调
- RLHF
#### ChatGPT
与InstructGPT的区别仅在于数据采集方式
### InstructGPT介绍
SFT->RM->PPO
#### SFT

#### RLHF
- RM：由标注者对答案排序

- PPO：

### 介绍对比学习

### LoRA微调的原理

### Coding：二叉树的序列化与反序列化

