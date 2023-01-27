---
title: hexo实现文档加密
tags: []
index_img: /img/example.png
categories:
  - 解决方案
date: 2023-01-26 23:44:24
---
### Hexo+Obsidian+Git
实现多端同步，实质上也就不同PC端，安卓obsidian会卡死。

### 文档加密
安装`hexo-blog-encrypt`并添加`password`字段
### 不在首页展示
1. ~~一般说是添加`notshow`字段，但这个对`fluid`主题无效~~
2. `fluid`主题得用`hide`
### 很坑的站内链接
应该用`{% post_link <不要目录直接文档名> '显示文字' %}`，和别处说的不一样，不懂

