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

## Live2D Widget

当前站点的 Live2D 看板娘不是本地静态资源，也不是 git 子模块，而是直接通过 CDN 注入。

脚本入口在：

- `themes/fluid/layout/layout.ejs`

当前写法：

```html
<script src="https://fastly.jsdelivr.net/npm/live2d-widgets@1.0.0/dist/autoload.js"></script>
```

如果你只是想继续使用默认看板娘，一般不用再动它。

### 想替换版本

直接改这行脚本地址即可，例如把 `1.0.0` 换成你想固定的版本号。

### 想关闭看板娘

删除或注释掉 `themes/fluid/layout/layout.ejs` 里的这行 `<script>`。

### 为什么不用本地目录或子模块

- 之前 `source/live2d-widget` 留下过坏掉的子模块记录，会导致 GitHub Actions 构建失败
- 这个组件本质上是前端静态脚本，用 CDN 更省维护
- 如果以后上游更新，你只需要改脚本版本，不需要同步整个仓库

### 什么时候适合改回本地托管

只有在下面几种情况才建议自己托管：

- 你要改 `autoload.js` 或 widget 行为
- 你要固定一份完全可控的资源副本
- 你不希望运行时依赖外部 CDN

这种情况下，优先考虑把静态文件直接放进 `source/`，不建议再用 git submodule。

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
