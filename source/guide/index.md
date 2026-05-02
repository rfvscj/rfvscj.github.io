---
title: 站点维护
layout: page
date: 2026-04-03 00:00:00
---

# 站点维护入口

这个页面是博客的站内维护说明，目标不是解释主题本身，而是约束以后如何持续维护这个仓库。

## 当前维护原则

- 优先改根配置和 `source/`，尽量不直接改 `themes/fluid/`
- 先维护“站点质量”，再追求“功能增加”
- 首页和 About 负责传达身份，文章页负责沉淀内容
- 明显只是占位的文章不要长期公开挂在首页
- 如果长期维护约定发生变化，要同步更新仓库里的 `.codex/skills/blog-manager/`

## 当前风格入口

- 站点基础信息：`_config.yml`
- Fluid 主题配置：`_config.fluid.yml`
- 自定义样式：`source/css/custom-theme.css`
- About 页面正文：`source/about/index.md`
- 博客管理 skill：`.codex/skills/blog-manager/`
- 技术问答沉淀 skill：`.codex/skills/blog-note-curator/`

## 文章顶部格式规范

以后新文章默认遵循这一套 front matter：

```yml
---
title: 文章标题
date: 2026-04-23 10:00:00
updated:
categories:
  - LLM必备
tags:
  - attention
  - training
index_img: /img/bg1.png
excerpt: 一句话说明这篇文章解决什么问题，尽量控制在 40 到 80 个字。
published: true
---
```

### 字段规则

- `title`
  必填。尽量用读者能一眼看懂的标题，不要只写缩写或内部代号。
- `date`
  必填。表示首次公开时间。
- `updated`
  可选。只有在文章经过实质性重写、补充或校正时再填，不要每次小改都写。
- `categories`
  必填。当前默认只放一个一级栏目，避免一篇文章挂太多分类。
- `tags`
  可选。用来补充具体主题，宁少勿滥。
- `index_img`
  可选。首页卡片封面图。重要文章、系列文章、首页精选文章建议填写；普通短文可以留空，留空时会走主题默认封面。
- `excerpt`
  强烈建议填写。它决定首页和列表页的预览质量，不要把摘要留给自动截断。
- `published`
  必填。公开文章写 `true`，未完成或占位稿写 `false`。

### 什么时候必须手写 `excerpt`

以下情况不要依赖自动摘要，直接写 `excerpt`：

- 文章开头是定义、公式、代码块
- 文章前两段只是铺垫，不适合做首页预览
- 你希望首页卡片明确说明文章价值

### `index_img` 使用规则

- 优先使用 `source/img/` 下的站内图片
- 系列文章可以共用一张统一封面
- 如果没有合适图片，宁可留空，也不要为了“有图”塞无关图片

### 隐藏与废弃规则

- 未完成文章：`published: false`
- 不再使用 `notshow`
- 不再新增 `hide`

`published: false` 是当前唯一推荐的隐藏方式，因为它最清晰，也最不依赖主题细节。

### 当前主题里的实际展示

当前主题配置下，文章顶部和首页列表的主要显示逻辑是：

- 文章页显示：发布时间、字数、预计阅读时长
- 文章页默认不显示：更新时间
- 首页列表显示：时间、分类、标签
- 首页列表默认封面：如果没写 `index_img`，使用 `_config.fluid.yml` 里的 `post.default_index_img`

如果以后要改这些展示开关，优先修改 `_config.fluid.yml`，不要靠给每篇文章塞特殊字段硬控。

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
  intro: "关注 LLM、GPU、系统与工程，也保留一部分对行业和个人选择的长期记录。"
```

### 4. 修改首页副标题

编辑 `_config.fluid.yml`：

```yml
index:
  slogan:
    text: "记录 LLM、GPU、系统基础、工程实践，以及那些需要长期观察的问题"
```

### 5. 修改站点标题和描述

编辑 `_config.yml`：

```yml
title: "叔莫少州令"
subtitle: "写 LLM、系统、GPU 与工程判断，也写长期主义下的个人思考"
description: "一个围绕 LLM、GPU、系统基础、工程实践与长期判断持续更新的个人博客。"
```

## 第一轮接管后的栏目策略

当前公开栏目优先保留这些方向：

- `LLM必备`
- `GPU相关`
- `OS&网络`
- `思考`

以下内容可以保留，但不应继续无序扩张：

- `杂项`
- `CV必备`
- `Triton算子`
- `行业展望`

后续新增文章时，优先判断它是：

1. 能沉淀成长期内容的技术文章
2. 有判断增量的思考文章
3. 只是临时笔记或占位提纲

第 3 类不要直接长期公开；至少要补成可读稿，或者先隐藏。

## 技术问答如何沉淀为笔记

在这个项目里回答技术问题时，先完整回答当前问题，再判断是否需要整理成博客笔记。适合沉淀的内容包括可复用的概念解释、调试路径、工程流程、命令备忘和长期会重复遇到的踩坑点。

整理前先用 `.codex/skills/blog-note-curator/scripts/find_related_posts.py` 检查相关旧文。同类问题优先更新已有文章；只有没有合适归宿时才新建文章。由问答临时整理出的新文章默认写 `published: false`，等内容足够完整后再公开。

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

## 文章整理规则

适合继续公开的文章，至少满足其中一条：

- 已经能独立阅读，不需要上下文补全
- 虽然短，但能传达一个完整概念
- 能作为后续系列文章的稳定入口

应该考虑隐藏或重写的文章：

- 只有一句“以后再补”
- 只是栏目占位
- 只有零散公式，没有说明背景和用途
- 标题与内容范围明显不匹配

隐藏方式建议优先使用文章 front matter：

```yml
published: false
```

比删除更稳妥，因为这样不会丢失素材。

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

## 接管约定

如果后续由 Codex 继续维护这个博客，默认先读取：

1. `.codex/skills/blog-manager/SKILL.md`
2. `.codex/skills/blog-manager/references/project-map.md`
3. 当前任务直接相关的配置或页面文件

除非任务确实跨很多区域，否则不要再从零扫描整个仓库。
