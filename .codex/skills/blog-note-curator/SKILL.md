---
name: blog-note-curator
description: Answer technical questions in /Users/rfvscj/workspace/rfvscj.github.io and maintain durable blog notes afterward. Use when the user asks a technical question, debugging question, concept explanation, engineering workflow question, or project maintenance question in this blog repository and the answer may be worth preserving as a post under source/_posts/. First answer the user directly, then decide whether to create a new note, update an existing related note, or skip note maintenance. Avoid duplicate notes by checking existing posts before writing.
---

# Blog Note Curator

Use this skill after answering the user's technical question. The goal is to opportunistically turn reusable answers into blog notes without interrupting the main response.

## Workflow

1. Answer the user's question first.
2. Decide whether note maintenance is warranted.
3. Check existing posts for related notes before creating anything.
4. Update the best existing note when it covers the same concept or workflow.
5. Create a new post only when no existing note is a good home.
6. Keep drafts unpublished unless the note is already coherent enough for the public blog.

## When To Maintain Notes

Maintain a note when the answer contains durable knowledge, such as:

- a reusable technical explanation
- a debugging pattern likely to recur
- a command sequence or workflow worth remembering
- a comparison, rule of thumb, or implementation pattern
- a blog/project maintenance convention

Skip note maintenance when the request is:

- a one-off command result or status check
- purely conversational
- too narrow to be useful later
- sensitive, private, or unsuitable for publishing
- already fully covered by an existing note and no meaningful update is needed

If uncertain, prefer adding a short unpublished draft or updating an existing draft over creating a public post.

## Duplicate Check

Run the helper before editing posts:

```bash
python3 .codex/skills/blog-note-curator/scripts/find_related_posts.py "question or proposed title"
```

Use the output as a starting point, then read the top candidates before deciding. Treat scores as advisory, not authoritative.

Update an existing post when the new answer is the same topic, a missing section, a correction, or a closely related example. Create a new post when the answer would make the existing post incoherent or spans a distinct topic.

## Placement

Read [references/taxonomy.md](references/taxonomy.md) when choosing a category, title, tags, or publication status.

Default target root:

```text
source/_posts/
```

Use the repository front matter convention:

```yaml
---
title: 文章标题
date: YYYY-MM-DD HH:mm:ss
updated:
categories:
  - LLM必备
tags:
  - topic
index_img:
excerpt: 一句话说明这篇文章解决什么问题，尽量控制在 40 到 80 个字。
published: false
---
```

Set `published: false` for quick notes, partial notes, raw troubleshooting records, or anything that still reads like an answer transcript. Set `published: true` only when the post is coherent as an article.

When updating a post substantially, set `updated` to the current local time in `Asia/Shanghai`. Do not change `date` on updates.

## Writing Shape

Prefer concise Chinese notes unless the surrounding article is already English. Rewrite the answer into article form rather than pasting a chat transcript.

Useful structure:

- problem or question
- short answer
- reasoning or mechanism
- practical checklist, command, or example
- pitfalls or related notes

Keep code blocks runnable and commands scoped to the repository when applicable.
