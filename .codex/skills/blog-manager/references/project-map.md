# Project Map

## Purpose

This repository is a personal blog built with Hexo and the Fluid theme. The current editorial direction is LLM, GPU, systems, engineering practice, industry judgment, and long-term personal thinking.

## Core Stack

- Static site generator: `Hexo` 8.x
- Theme: `Fluid`
- Package manager: `npm`
- Deployment target: GitHub Pages via `gh-pages`

## High-Value Files

- `_config.yml`
  Site metadata, URL, permalink rules, deploy settings, Hexo writing behavior.
- `_config.fluid.yml`
  Theme-level configuration including navbar, banners, about settings, colors, dark mode, plugins, and custom CSS hooks.
- `scaffolds/post.md`
  Default post front matter template. Keep this aligned with the repository's preferred metadata fields.
- `source/css/custom-theme.css`
  Main custom visual layer. Prefer editing this instead of patching theme source for most branding or polish work.
- `source/about/index.md`
  About page body copy.
- `source/guide/index.md`
  In-site maintenance guide for future edits.
- `.codex/skills/blog-note-curator/`
  Project-local skill for answering durable technical questions and then creating or updating related blog notes without duplicating existing posts.
- `package.json`
  Project scripts: `build`, `clean`, `server`, `deploy`.
- `README.md`
  Short local development entrypoint and repo editing principles.

## Content Layout

- `source/_posts/`
  Main article corpus. Content is grouped by top-level Chinese category folders such as `LLM必备`, `GPU相关`, `OS&网络`, `思考`, `杂项`, `CV必备`, `Triton算子`, `行业展望`.
- `source/about/`
  About page source.
- `source/guide/`
  Maintainer guide page.
- `source/img/`
  Site images and blog-owned visual assets.
- `source/images/`
  Older image assets, likely imported or pasted images.

## Theme And Customization Boundaries

- Prefer modifying `_config.yml`, `_config.fluid.yml`, and `source/` before touching `themes/fluid/`.
- `themes/fluid/` exists in-repo, but direct theme source edits should be the exception.
- The current custom design language is implemented mostly in `source/css/custom-theme.css`.

## Current Site Identity

- Site title: `叔莫少州令`
- Primary subtitle direction: record LLM, systems, engineering, and long-term concerns
- Language: `zh-CN`
- Timezone: `Asia/Shanghai`
- Public URL: `https://rfvscj.github.io`

## Operational Commands

Run from repository root:

```bash
npm install
npm run clean
npm run server
npm run build
npm run deploy
```

## Current Maintenance Conventions

- Prefer concise structural summaries over full repository re-scans.
- Treat this repository as an actively maintained long-term blog, not a throwaway theme demo.
- Homepage and About should explain identity clearly before adding more features.
- Placeholder outlines should usually be hidden with `published: false` until they become readable posts.
- Main public navigation should stay focused on home, articles, categories, maintenance, and about.
- Preferred post front matter fields are `title`, `date`, `updated`, `categories`, `tags`, `index_img`, `excerpt`, and `published`.
- Prefer `published: false` as the only standard hiding mechanism; do not rely on legacy `notshow`, and avoid adding new `hide` usage.
- Prefer writing explicit `excerpt` values for important posts instead of relying on automatic truncation.
- If a task creates new lasting conventions, update this project map and the parent `SKILL.md`.
- When a technical Q&A answer is worth preserving, use `blog-note-curator`: answer first, check related posts, update an existing note when possible, and create a new unpublished post only when there is no good home.
