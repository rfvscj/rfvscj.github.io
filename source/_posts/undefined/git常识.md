---
title: git小常识
categories:
  - undefined
date: 2023-01-15 06:27:39
tags:
---
### git 换行符问题
Git: ‘LF will be replaced by CRLF the next time Git touches it
原因：Windows 使用 CRLF，Linux 和 git 使用 LF
1. 对于 Windows 系统（默认，推荐）
```
# 提交时转换为LF，检出时转换为CRLF
git config --global core.autocrlf true
```
或仅在 Windows 上开发操作时
```
# 提交检出均不转换
git config --global core.autocrlf false
```
2. 对于 Linux 系统
```
# 提交时转换为LF，检出时不转换
git config --global core.autocrlf input
```
解决方案：
不管，或修改 .gitattributes

### i18n
即 internationalization，i+18 个字符+n，自动多国语言。

### .gitignore
顾名思义，git 忽略其中指定文件/文件夹的改动

### .gitkeep
只是为了使文件夹不再为空，从而不会被忽视，命名为约定俗成

### .gitattribute
定义一些属性
