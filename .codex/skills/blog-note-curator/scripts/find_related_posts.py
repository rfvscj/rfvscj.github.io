#!/usr/bin/env python3
"""Find existing Hexo posts related to a question or proposed note title."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_POSTS_ROOT = Path("source/_posts")


def read_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    frontmatter = {}
    body = text
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            _, raw_fm, body = parts
            frontmatter = parse_frontmatter(raw_fm)
    title = frontmatter.get("title") or path.stem
    categories = frontmatter.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]
    return {
        "path": str(path),
        "title": title,
        "categories": categories,
        "tags": frontmatter.get("tags") or [],
        "excerpt": frontmatter.get("excerpt") or "",
        "text": f"{title}\n{frontmatter.get('excerpt', '')}\n{body}",
    }


def parse_frontmatter(raw: str) -> dict:
    data: dict[str, object] = {}
    current_key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            value = line[4:].strip().strip('"').strip("'")
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(value)
            continue
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            current_key = match.group(1)
            value = match.group(2).strip()
            if value == "":
                data[current_key] = []
            else:
                data[current_key] = value.strip('"').strip("'")
    return data


def tokens(text: str) -> set[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9][a-z0-9_+\-.]{1,}", lowered))
    cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
    grams = {"".join(cjk[i : i + 2]) for i in range(max(0, len(cjk) - 1))}
    grams.update("".join(cjk[i : i + 3]) for i in range(max(0, len(cjk) - 2)))
    return {item for item in words | grams if item}


def ascii_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_+\-.]{1,}", text.lower()))


def score(query: str, post: dict) -> float:
    query_tokens = tokens(query)
    post_text = post["text"]
    post_tokens = tokens(post_text)
    if not query_tokens or not post_tokens:
        return 0.0

    overlap = query_tokens & post_tokens
    base = len(overlap) / max(1, len(query_tokens))

    query_ascii = ascii_tokens(query)
    post_ascii = ascii_tokens(post_text)
    ascii_overlap = query_ascii & post_ascii
    ascii_score = len(ascii_overlap) / max(1, len(query_ascii)) if query_ascii else 0

    title_tokens = tokens(post["title"])
    title_score = len(query_tokens & title_tokens) / max(1, len(query_tokens))

    path_tokens = tokens(post["path"])
    path_score = len(query_tokens & path_tokens) / max(1, len(query_tokens))

    category_text = " ".join(post.get("categories", []))
    category_score = len(query_tokens & tokens(category_text)) / max(1, len(query_tokens))

    return base + (ascii_score * 1.5) + (title_score * 1.2) + (path_score * 0.6) + (category_score * 0.4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Question, topic, or proposed note title")
    parser.add_argument("--posts-root", default=str(DEFAULT_POSTS_ROOT))
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    posts_root = Path(args.posts_root)
    if not posts_root.exists():
        raise SystemExit(f"posts root not found: {posts_root}")

    results = []
    for path in sorted(posts_root.rglob("*.md")):
        post = read_post(path)
        value = score(args.query, post)
        if value > 0:
            results.append(
                {
                    "score": round(value, 3),
                    "path": post["path"],
                    "title": post["title"],
                    "categories": post["categories"],
                    "excerpt": post["excerpt"],
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    print(json.dumps(results[: args.top_k], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
