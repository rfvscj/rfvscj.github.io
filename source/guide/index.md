---
title: 配置指南
layout: page
date: 2026-04-03 00:00:00
---

# 博客配置指南

这个页面是站内版说明书，主要告诉你以后怎么自己换背景、换文案、换颜色，而不用去动主题源码。

## 当前风格入口

- 站点基础信息：`_config.yml`
- Fluid 主题配置：`_config.fluid.yml`
- 自定义样式：`source/css/custom-theme.css`
- About 页面正文：`source/about/index.md`

## 最常改的配置

### 1. 修改首页背景

编辑 `_config.fluid.yml`：

```yml
index:
  banner_img: /img/bg6.png
```

把图片放到 `source/img/`，然后把路径改成你的新图，例如：

```yml
index:
  banner_img: /img/your-home-bg.jpg
```

### 2. 修改文章页背景

编辑 `_config.fluid.yml`：

```yml
post:
  banner_img: /img/bg3.png
```

### 3. 修改 About 页背景和头像

编辑 `_config.fluid.yml`：

```yml
about:
  banner_img: /img/bg2.png
  avatar: /img/myhead.png
  name: "叔莫少州令"
  intro: "记录技术、判断和长期关注的问题。"
```

### 4. 修改首页副标题

编辑 `_config.fluid.yml`：

```yml
index:
  slogan:
    text: "记录 LLM、系统、工程与长期关注的问题"
```

### 5. 修改站点标题和描述

编辑 `_config.yml`：

```yml
title: "叔莫少州令"
subtitle: "在理性和幻想之间整理生活"
description: "一个记录 LLM、GPU、系统基础、行业判断与个人思考的博客。"
```

## 如何换背景图

推荐做法：

1. 把新图片放进 `source/img/`
2. 在 `_config.fluid.yml` 里改 `banner_img`
3. 执行 `npm run build` 或 `npm run server`

推荐保留这些场景各自一张图：

- 首页：`index.banner_img`
- 文章页：`post.banner_img`
- About 页：`about.banner_img`
- 归档页：`archive.banner_img`
- 分类页：`category.banner_img`
- 标签页：`tag.banner_img`

## 如何改主题颜色

编辑 `_config.fluid.yml` 里的 `color`：

```yml
color:
  navbar_bg_color: "#5a4d8f"
  board_color: "rgba(255, 251, 255, 0.86)"
  post_link_color: "#7d63d6"
  link_hover_color: "#ff7ab6"
```

如果主题配置不够，再去改：

- `source/css/custom-theme.css`

建议优先改这个文件顶部的颜色变量。

## 自定义样式说明

`source/css/custom-theme.css` 负责这些内容：

- 首页和内页的渐变氛围
- 半透明卡片
- 统一站点配色与卡片样式
- 标题、导航、文章卡片的视觉强化
- 背景装饰光晕和细节

以后如果想整体切风格，优先改这个文件，不要直接改 `themes/fluid/` 里的源码。

## 发布

当前部署配置在 `_config.yml`：

```yml
deploy:
  type: git
  repo: https://github.com/rfvscj/rfvscj.github.io
  branch: gh-pages
```

发布前建议：

```bash
npm run clean
npm run build
```

如果构建正常，再执行：

```bash
npm run deploy
```
