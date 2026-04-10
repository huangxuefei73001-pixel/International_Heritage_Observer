# 国际遗产观察 Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-stage, evidence-first local skill that parses the existing "国际遗产观察" archive, creates a structured article library, answers natural-language research questions from that library only, and packages the workflow as a reusable Codex skill.

**Architecture:** Use a small Python project with standard-library parsing only. Parse each `.docx` archive into normalized JSON records, build a local JSONL library plus a compact index file, expose a query CLI that turns natural questions into keyword-based retrieval and evidence-first summaries, then document the workflow in a skill that instructs Codex to rely on this local library instead of open-ended knowledge.

**Tech Stack:** Python 3 standard library, pytest, Markdown skill docs, local JSON/JSONL data files

---

## File Structure

- Create: `pyproject.toml`
- Create: `src/guoji_yichan_guancha/__init__.py`
- Create: `src/guoji_yichan_guancha/models.py`
- Create: `src/guoji_yichan_guancha/parser.py`
- Create: `src/guoji_yichan_guancha/library.py`
- Create: `src/guoji_yichan_guancha/query.py`
- Create: `src/guoji_yichan_guancha/cli.py`
- Create: `scripts/build_library.py`
- Create: `scripts/query_library.py`
- Create: `skills/guoji-yichan-guancha/SKILL.md`
- Create: `tests/fixtures/sample_article.docx`
- Create: `tests/test_parser.py`
- Create: `tests/test_library.py`
- Create: `tests/test_query.py`
- Create: `data/.gitkeep`

## Task 1: Scaffold The Python Project And Lock The Article Schema

**Files:**
- Create: `pyproject.toml`
- Create: `src/guoji_yichan_guancha/__init__.py`
- Create: `src/guoji_yichan_guancha/models.py`
- Test: `tests/test_library.py`

- [ ] **Step 1: Write the failing schema test**

```python
from guoji_yichan_guancha.models import ArticleRecord


def test_article_record_to_document_uses_required_fields():
    record = ArticleRecord(
        article_id="abc123",
        title="韩国召开第48届世界遗产大会联席工作会",
        published_at="2026-03-20 11:25",
        channel="国际遗产观察",
        category="韩国",
        source_url="https://mp.weixin.qq.com/s/abamHniN0MaGiOCA54LIOQ",
        local_source_path="/tmp/sample.docx",
        content_text="韩国日前召开第48届世界遗产大会跨部门工作会。",
        content_html_excerpt="<p>韩国日前召开第48届世界遗产大会跨部门工作会。</p>",
        parse_status="ok",
        tags_auto=["韩国", "世界遗产大会"],
    )

    document = record.to_document()

    assert document["article_id"] == "abc123"
    assert document["title"].startswith("韩国召开")
    assert document["category"] == "韩国"
    assert document["tags_auto"] == ["韩国", "世界遗产大会"]
```

- [ ] **Step 2: Run the test to verify RED**

Run: `pytest tests/test_library.py::test_article_record_to_document_uses_required_fields -v`

Expected: FAIL with `ModuleNotFoundError` or missing `ArticleRecord`

- [ ] **Step 3: Write the minimal project scaffold**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "guoji-yichan-guancha"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/guoji_yichan_guancha/__init__.py
"""Local tools for the 国际遗产观察 research skill."""
```

```python
# src/guoji_yichan_guancha/models.py
from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ArticleRecord:
    article_id: str
    title: str
    published_at: str
    channel: str
    category: str
    source_url: str
    local_source_path: str
    content_text: str
    content_html_excerpt: str
    parse_status: str
    tags_auto: list[str]

    def to_document(self) -> dict:
        return asdict(self)
```

- [ ] **Step 4: Run the test to verify GREEN**

Run: `pytest tests/test_library.py::test_article_record_to_document_uses_required_fields -v`

Expected: PASS

- [ ] **Step 5: Commit the scaffold**

```bash
git add pyproject.toml src/guoji_yichan_guancha/__init__.py src/guoji_yichan_guancha/models.py tests/test_library.py
git commit -m "feat: add article record schema"
```

## Task 2: Parse WeChat `.docx` Archives Into Stable Article Records

**Files:**
- Create: `src/guoji_yichan_guancha/parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/sample_article.docx`

- [ ] **Step 1: Write the failing parser test**

```python
from pathlib import Path

from guoji_yichan_guancha.parser import parse_docx_article


def test_parse_docx_article_reads_metadata_and_falls_back_to_filename():
    fixture = Path("tests/fixtures/sample_article.docx")

    record = parse_docx_article(fixture, category="韩国")

    assert record.title == "sample_article"
    assert record.published_at == "2026-03-20 11:25"
    assert record.category == "韩国"
    assert record.source_url == "https://mp.weixin.qq.com/s/example"
    assert "世界遗产大会跨部门工作会" in record.content_text
    assert record.parse_status == "title_fallback"
```

- [ ] **Step 2: Run the test to verify RED**

Run: `pytest tests/test_parser.py::test_parse_docx_article_reads_metadata_and_falls_back_to_filename -v`

Expected: FAIL because `parse_docx_article` does not exist

- [ ] **Step 3: Add the parser implementation**

```python
# src/guoji_yichan_guancha/parser.py
from __future__ import annotations

import hashlib
import html
import quopri
import re
import zipfile
from pathlib import Path

from .models import ArticleRecord


DOC_MARKER = b"Content-Location: file:///C:/fake/document.html\n\n"
NOISE_LINES = {"阅读", "赞", "分享", "推荐", "留言", "国际遗产观察", "(unknown)"}


def _pick_class(html_text: str, class_name: str) -> str:
    match = re.search(fr'<[^>]+class="{class_name}"[^>]*>(.*?)</[^>]+>', html_text, flags=re.S)
    if not match:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1)).strip())


def _clean_body(html_text: str) -> str:
    if "</blockquote>" in html_text:
        html_text = html_text.split("</blockquote>", 1)[1]
    html_text = re.sub(r"<(script|style).*?</\\1>", "", html_text, flags=re.S | re.I)
    html_text = re.sub(r"<br\\s*/?>", "\n", html_text, flags=re.I)
    html_text = re.sub(r"</(p|div|section|h1|h2|h3|li|blockquote|hr)>", "\n", html_text, flags=re.I)
    html_text = re.sub(r"<[^>]+>", "", html_text)
    text = html.unescape(html_text)
    lines = [re.sub(r"\\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line and line not in NOISE_LINES)


def parse_docx_article(path: Path, category: str) -> ArticleRecord:
    with zipfile.ZipFile(path) as archive:
        mht = archive.read("word/afchunk.mht")
    body = mht.split(DOC_MARKER, 1)[1].split(b"------=mhtDocumentPart", 1)[0]
    html_text = quopri.decodestring(body).decode("utf-8", errors="ignore")

    raw_title = _pick_class(html_text, "title")
    title = path.stem if not raw_title or raw_title == "(unknown)" else raw_title
    parse_status = "title_fallback" if title == path.stem else "ok"

    url_match = re.search(r'原文地址: <a href="([^"]+)"', html_text)
    content_text = _clean_body(html_text)
    article_id = hashlib.sha1(f"{path}|{title}".encode("utf-8")).hexdigest()[:16]

    return ArticleRecord(
        article_id=article_id,
        title=title,
        published_at=_pick_class(html_text, "create_time"),
        channel=_pick_class(html_text, "nick_name") or "国际遗产观察",
        category=category,
        source_url=url_match.group(1) if url_match else "",
        local_source_path=str(path),
        content_text=content_text,
        content_html_excerpt=html_text[:1200],
        parse_status=parse_status,
        tags_auto=[],
    )
```

- [ ] **Step 4: Build the fixture and verify GREEN**

Create `tests/fixtures/sample_article.docx` by copying one known-small archive from the source library, then run:

`pytest tests/test_parser.py::test_parse_docx_article_reads_metadata_and_falls_back_to_filename -v`

Expected: PASS

- [ ] **Step 5: Commit the parser**

```bash
git add src/guoji_yichan_guancha/parser.py tests/test_parser.py tests/fixtures/sample_article.docx
git commit -m "feat: parse wechat article archives"
```

## Task 3: Build The Structured Local Library

**Files:**
- Create: `src/guoji_yichan_guancha/library.py`
- Create: `scripts/build_library.py`
- Modify: `tests/test_library.py`
- Create: `data/.gitkeep`

- [ ] **Step 1: Write the failing library-build test**

```python
from pathlib import Path

from guoji_yichan_guancha.library import build_library


def test_build_library_writes_jsonl_and_summary(tmp_path):
    source_dir = Path("tests/fixtures")
    output_dir = tmp_path / "library"

    result = build_library(source_dir, output_dir)

    assert result["article_count"] == 1
    assert (output_dir / "articles.jsonl").exists()
    assert (output_dir / "summary.json").exists()
```

- [ ] **Step 2: Run the test to verify RED**

Run: `pytest tests/test_library.py::test_build_library_writes_jsonl_and_summary -v`

Expected: FAIL because `build_library` does not exist

- [ ] **Step 3: Implement the library builder**

```python
# src/guoji_yichan_guancha/library.py
from __future__ import annotations

import json
from pathlib import Path

from .parser import parse_docx_article


def build_library(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(source_dir.rglob("*.docx")):
        category = path.parent.name
        records.append(parse_docx_article(path, category=category))

    jsonl_path = output_dir / "articles.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record.to_document(), ensure_ascii=False) + "\n")

    summary = {
        "article_count": len(records),
        "categories": sorted({record.category for record in records}),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    return summary
```

```python
# scripts/build_library.py
from pathlib import Path

from guoji_yichan_guancha.library import build_library


SOURCE_DIR = Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取")
OUTPUT_DIR = Path("data/library")


if __name__ == "__main__":
    summary = build_library(SOURCE_DIR, OUTPUT_DIR)
    print(summary)
```

- [ ] **Step 4: Run the test to verify GREEN**

Run: `pytest tests/test_library.py::test_build_library_writes_jsonl_and_summary -v`

Expected: PASS

- [ ] **Step 5: Smoke-test the real library build**

Run: `python3 scripts/build_library.py`

Expected: prints a summary dict with article count and categories, and writes `data/library/articles.jsonl`

- [ ] **Step 6: Commit the library builder**

```bash
git add src/guoji_yichan_guancha/library.py scripts/build_library.py tests/test_library.py data/.gitkeep
git commit -m "feat: build structured article library"
```

## Task 4: Add Natural-Language Query And Evidence-First Output

**Files:**
- Create: `src/guoji_yichan_guancha/query.py`
- Create: `src/guoji_yichan_guancha/cli.py`
- Create: `scripts/query_library.py`
- Create: `tests/test_query.py`

- [ ] **Step 1: Write the failing query test**

```python
from pathlib import Path

from guoji_yichan_guancha.query import answer_question


def test_answer_question_returns_evidence_first_summary(tmp_path):
    library_path = tmp_path / "articles.jsonl"
    library_path.write_text(
        '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/example","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}\\n',
        encoding="utf-8",
    )

    answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=3)

    assert "基于库内文章归纳" in answer
    assert "韩国召开第48届世界遗产大会联席工作会" in answer
    assert "https://mp.weixin.qq.com/s/example" in answer
```

- [ ] **Step 2: Run the test to verify RED**

Run: `pytest tests/test_query.py::test_answer_question_returns_evidence_first_summary -v`

Expected: FAIL because `answer_question` does not exist

- [ ] **Step 3: Implement the query engine and CLI**

```python
# src/guoji_yichan_guancha/query.py
from __future__ import annotations

import json
import re
from pathlib import Path


def _tokenize(question: str) -> list[str]:
    return [token for token in re.split(r"[\\s，。、“”‘’：:？?（）()\\-]+", question) if token]


def _score(document: dict, tokens: list[str]) -> int:
    haystack = " ".join([document["title"], document["category"], document["content_text"]])
    return sum(3 if token in document["title"] else 1 for token in tokens if token and token in haystack)


def answer_question(question: str, library_path: Path, limit: int = 5) -> str:
    documents = []
    with library_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                documents.append(json.loads(line))

    tokens = _tokenize(question)
    ranked = sorted(
        ((doc, _score(doc, tokens)) for doc in documents),
        key=lambda item: (item[1], item[0]["published_at"]),
        reverse=True,
    )
    matches = [doc for doc, score in ranked if score > 0][:limit]
    if not matches:
        return "当前库内没有足够材料支持该回答。"

    lines = ["基于库内文章归纳："]
    lines.append(f"问题理解：{question}")
    lines.append("")
    lines.append("证据文章：")
    for doc in matches:
        lines.append(f"- {doc['title']} | {doc['published_at']} | {doc['category']} | {doc['source_url']}")
    return "\\n".join(lines)
```

```python
# src/guoji_yichan_guancha/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .query import answer_question


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--library", default="data/library/articles.jsonl")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    print(answer_question(args.question, Path(args.library), limit=args.limit))


if __name__ == "__main__":
    main()
```

```python
# scripts/query_library.py
from guoji_yichan_guancha.cli import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify GREEN**

Run: `pytest tests/test_query.py::test_answer_question_returns_evidence_first_summary -v`

Expected: PASS

- [ ] **Step 5: Smoke-test a real question against the built library**

Run:

`python3 scripts/query_library.py "2026年韩国的世界遗产动态有什么？" --library data/library/articles.jsonl --limit 5`

Expected: prints an evidence-first answer that cites relevant Korean world heritage articles from the local library

- [ ] **Step 6: Commit the query workflow**

```bash
git add src/guoji_yichan_guancha/query.py src/guoji_yichan_guancha/cli.py scripts/query_library.py tests/test_query.py
git commit -m "feat: add evidence-first question answering"
```

## Task 5: Package The Workflow As A Reusable Codex Skill

**Files:**
- Create: `skills/guoji-yichan-guancha/SKILL.md`

- [ ] **Step 1: Write the failing skill-usage pressure test**

Use this manual pressure scenario before writing the skill:

`用户提问：“最近韩国有什么世界遗产的动态？”`

Expected RED behavior without the new skill:

- Agent answers too broadly
- Agent mixes library evidence and generic knowledge
- Agent fails to cite exact articles

Record the actual failure mode in your notes before continuing.

- [ ] **Step 2: Write the skill document**

```markdown
---
name: guoji-yichan-guancha
description: Use when answering work or research questions about heritage protection, museums, planning, world heritage, or related concepts using the local 国际遗产观察 article library
---

# 国际遗产观察

## Overview

This skill answers heritage research questions from the local 国际遗产观察 library only. It is evidence-first: retrieve library articles, summarize cautiously, and state limits when the library is insufficient.

## When To Use

- The question is about heritage protection, museums, planning, interpretation, tourism, UNESCO, ICOMOS, ICCROM, or world heritage
- The user wants article-backed explanation, research clues, report material, or recent dynamics
- The answer should come from the 国际遗产观察 library rather than open-ended knowledge

## Required Workflow

1. Interpret the natural-language question into retrieval dimensions: object, theme, time, task type.
2. Run:
   `python3 scripts/query_library.py "<user question>" --library data/library/articles.jsonl --limit 5`
3. Use the command output as the basis for the answer.
4. If the output says the library is insufficient, repeat that limit to the user. Do not fill the gap with generic background knowledge.
5. When useful, add 2-4 short report-ready takeaways, but mark them as "基于库内文章归纳".

## Common Mistakes

- Do not answer from memory when the library has no support.
- Do not hide uncertainty.
- Do not present inferred trends as if they are direct quotations.
```

- [ ] **Step 3: Verify the skill on a real query**

Run:

`python3 scripts/query_library.py "最近韩国有什么世界遗产的动态？" --library data/library/articles.jsonl --limit 5`

Then manually confirm the answer:

- cites relevant Korean articles
- uses evidence-first wording
- states limits instead of inventing facts

- [ ] **Step 4: Commit the skill package**

```bash
git add skills/guoji-yichan-guancha/SKILL.md
git commit -m "feat: add guoji yichan guancha skill"
```

## Task 6: Add A Manual Incremental Update Path

**Files:**
- Modify: `src/guoji_yichan_guancha/library.py`
- Modify: `scripts/build_library.py`
- Modify: `skills/guoji-yichan-guancha/SKILL.md`
- Modify: `tests/test_library.py`

- [ ] **Step 1: Write the failing incremental-build test**

```python
from pathlib import Path

from guoji_yichan_guancha.library import build_library


def test_build_library_skips_existing_source_urls(tmp_path):
    source_dir = Path("tests/fixtures")
    output_dir = tmp_path / "library"

    first = build_library(source_dir, output_dir)
    second = build_library(source_dir, output_dir)

    assert first["article_count"] == 1
    assert second["article_count"] == 1
    assert second["skipped_duplicates"] == 1
```

- [ ] **Step 2: Run the test to verify RED**

Run: `pytest tests/test_library.py::test_build_library_skips_existing_source_urls -v`

Expected: FAIL because duplicate skipping is not implemented

- [ ] **Step 3: Add duplicate-aware rebuilding**

```python
def build_library(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "articles.jsonl"
    seen_urls = set()
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    seen_urls.add(json.loads(line)["source_url"])

    records = []
    skipped_duplicates = 0
    for path in sorted(source_dir.rglob("*.docx")):
        record = parse_docx_article(path, category=path.parent.name)
        if record.source_url and record.source_url in seen_urls:
            skipped_duplicates += 1
            continue
        seen_urls.add(record.source_url)
        records.append(record)

    mode = "a" if jsonl_path.exists() else "w"
    with jsonl_path.open(mode, encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record.to_document(), ensure_ascii=False) + "\n")

    summary = {
        "article_count": len(records),
        "skipped_duplicates": skipped_duplicates,
        "categories": sorted({record.category for record in records}),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return summary
```

- [ ] **Step 4: Run the test to verify GREEN**

Run: `pytest tests/test_library.py::test_build_library_skips_existing_source_urls -v`

Expected: PASS

- [ ] **Step 5: Update the skill instructions for manual library refresh**

Add this section to `skills/guoji-yichan-guancha/SKILL.md`:

```markdown
## Refreshing The Library

When new article archives are added locally, rebuild the library with:

`python3 scripts/build_library.py`

If the rebuild reports skipped duplicates, keep the existing records and only use the newly added ones.
```

- [ ] **Step 6: Commit the incremental update path**

```bash
git add src/guoji_yichan_guancha/library.py scripts/build_library.py skills/guoji-yichan-guancha/SKILL.md tests/test_library.py
git commit -m "feat: support manual incremental library refresh"
```

## Self-Review

- Spec coverage:
  - Structured library: Tasks 1-3
  - Natural-language, non-template question handling: Task 4
  - Evidence-first answer style and boundary rules: Tasks 4-5
  - Reusable skill packaging: Task 5
  - Manual incremental update path: Task 6
- Placeholder scan:
  - No `TODO`, `TBD`, or deferred implementation markers remain in the plan body
- Type consistency:
  - `ArticleRecord`, `build_library`, and `answer_question` names are consistent across tasks

Plan complete and saved to `docs/superpowers/plans/2026-04-09-guoji-yichan-guancha-skill.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
