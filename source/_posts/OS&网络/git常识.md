---
title: Git 常用备忘
categories:
  - OS&网络
date: 2023-01-15 06:27:39
tags:
index_img: /img/bg0.png
excerpt: 记录几个真正常见的 Git 基础概念和踩坑点，包括换行符、.gitignore、.gitkeep 和 .gitattributes。
---

这篇记录几个开发里常见但容易混淆的 Git 基础点。

## Git 换行符问题

你经常会看到类似提示：

```text
LF will be replaced by CRLF the next time Git touches it
```

原因很简单：

- Windows 常用 `CRLF`
- Linux、macOS 和 Git 内部更常见 `LF`

### 对于 Windows 系统

```bash
# 提交时转换为LF，检出时转换为CRLF
git config --global core.autocrlf true
```

如果你明确想关闭自动转换，也可以：

```bash
# 提交检出均不转换
git config --global core.autocrlf false
```

### 对于 Linux / macOS

```bash
# 提交时转换为LF，检出时不转换
git config --global core.autocrlf input
```

更稳妥的做法，是在仓库里用 `.gitattributes` 统一声明文本文件规则，而不是完全依赖个人全局配置。

## i18n

`i18n` 是 `internationalization` 的缩写，中间有 18 个字符，所以写成 `i + 18 + n`。

## .gitignore

`.gitignore` 用来告诉 Git 忽略哪些文件或目录的改动，例如：

- 构建产物
- 本地缓存
- 临时文件
- 密钥和环境变量文件

## .gitkeep

Git 不会跟踪空目录，所以很多项目会放一个约定俗成的 `.gitkeep`，只是为了让目录能被保留下来。

## .gitattributes

`.gitattributes` 用来给路径定义属性，常见用途包括：

- 统一换行符
- 指定文本/二进制处理方式
- 指定 diff 或 merge 策略

如果你经常遇到跨平台换行符问题，真正值得优先了解的是 `.gitattributes`，它比口口相传的 Git 全局配置更稳定。
