---
name: blog-manager
description: Manage the personal blog in this repository with minimal re-discovery. Use when Codex is working on /Users/rfvscj/workspace/rfvscj.github.io for blog operations such as site structure review, Hexo or Fluid configuration changes, homepage or about page edits, article organization, publishing workflow changes, visual refreshes, content planning, or ongoing maintenance. Prefer this skill before re-reading the whole repository. Update this skill and its references in the same turn whenever the repo structure, editorial rules, page entrypoints, or maintenance workflow materially change.
---

# Blog Manager

Use this skill as the default entrypoint for work in this repository.

## Start Here

1. Assume the repository root is `/Users/rfvscj/workspace/rfvscj.github.io`.
2. Read [references/project-map.md](references/project-map.md) first.
3. Read only the files needed for the current task instead of re-scanning the entire repo.

## Default Workflow

1. Confirm the task type: structure review, content edit, design refresh, config change, build, or deploy.
2. Read the smallest relevant surface area.
3. Prefer changing root config and `source/` content before touching `themes/fluid/`.
4. Run a targeted verification step after edits when feasible, usually `npm run build` for site-wide changes.

## Targeted Entry Points

- Site identity, URL, deploy, permalink, writing settings:
  Read `_config.yml`.
- Theme behavior, navbar, banners, about page config, colors, plugins:
  Read `_config.fluid.yml`.
- Custom visual layer:
  Read `source/css/custom-theme.css`.
- About page body:
  Read `source/about/index.md`.
- In-repo maintenance notes:
  Read `source/guide/index.md`.
- Posts and taxonomy:
  Read `source/_posts/` selectively.
- Theme source:
  Read `themes/fluid/` only if root config and custom CSS cannot achieve the requested result.

## Working Rules

- Preserve the current stack: Hexo 8 + Fluid.
- Treat `source/_posts/` as the main content corpus.
- Keep new assets under `source/img/` unless the task clearly needs another location.
- Treat the blog as an incremental knowledge system: adding a new post should usually require only adding that post, not changing navigation, guide pages, or other posts.
- Keep cross-post coupling low. Do not maintain manual article lists in stable pages unless the articles form a durable series or have a strong dependency.
- Avoid broad repository scans unless the skill reference is stale or the task is genuinely cross-cutting.
- Do not create `agents/openai.yaml` for this skill unless the user explicitly asks for it.
- For post front matter conventions and top-of-post display rules, read `source/guide/index.md` and `scaffolds/post.md` before introducing new metadata fields.

## Skill Maintenance

Update this skill in the same turn when any of the following changes happen:

- Key file locations or repo structure change.
- The preferred workflow changes.
- New long-lived editorial or design conventions are established.
- New recurring maintenance commands become standard.
- Theme customization starts relying on files not listed in the current project map.

When updating, keep `SKILL.md` short and put durable project facts into `references/project-map.md`.

## Output Expectations

- When asked to “look at the project structure”, summarize from the project map first.
- When making changes, mention only the files actually needed for the task.
- When the task alters long-term maintenance knowledge, patch the skill before finishing.
