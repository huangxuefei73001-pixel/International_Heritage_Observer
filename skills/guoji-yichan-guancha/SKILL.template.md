---
name: guoji-yichan-guancha
description: Use when answering work or research questions about heritage protection, museums, planning, world heritage, heritage policy, or related concepts using the local 国际遗产观察 article library
---

# 国际遗产观察

## Overview

Use this skill when the answer should come from the local `国际遗产观察` article archive rather than open-ended model knowledge.

The workflow is evidence-first:

- interpret the natural-language question
- identify the user task shape: concept, trend, case, or dynamic
- identify evidence dimensions such as `报告资源` / `书刊资讯` / `会议新闻` / `政策动态` / `一般动态`
- query the local article library
- answer from matching articles only
- state limits when the library is insufficient

## When To Use

- The user is asking about heritage protection, museums, planning, UNESCO, ICOMOS, ICCROM, world heritage, interpretation, tourism, digital heritage, or related topics
- The user wants article-backed explanation, research clues, case studies, report material, or recent dynamics
- The answer should stay inside the `国际遗产观察` library

## Required Workflow

1. Treat the question as natural language. Do not force the user into a fixed template.
2. Run:

```bash
PYTHONPATH=__REPO_ROOT__/src python3 __REPO_ROOT__/scripts/query_library.py "<user question>" --library __REPO_ROOT__/data/library/articles.jsonl --limit 5
```

3. Use the command output as the answer base.
4. If the result says the library is insufficient, repeat that limit clearly to the user.
5. Do not fill evidence gaps with generic background knowledge unless the user later asks for a broader mode.
6. When the question is research-oriented, pay attention to the evidence mix:
   - concept questions should prefer reports and books over meeting notices
   - trend questions should combine reports, policy updates, and representative news
   - case questions should prefer concrete place-based or measure-based items over general announcements

## Refreshing The Library

### Full rebuild

```bash
PYTHONPATH=__REPO_ROOT__/src python3 __REPO_ROOT__/scripts/build_library.py --source-dir "<你的文章总目录>" --output-dir __REPO_ROOT__/data/library
```

### Incremental sync

```bash
PYTHONPATH=__REPO_ROOT__/src python3 __REPO_ROOT__/scripts/sync_incremental.py --source-dir "<你的新增文章目录>" --output-dir __REPO_ROOT__/data/library --log-dir __REPO_ROOT__/data/sync_logs
```

## Answer Style

- Prefer concise research-assistant language
- Distinguish `库内结论` from `证据文章`
- Keep the answer in this order when possible: `问题理解` -> `库内结论` -> `证据文章` -> `可直接用于写作的归纳`
- Surface evidence type labels when useful, such as `[报告资源]` or `[会议新闻]`
- Say `基于库内文章归纳` when summarizing across articles
- Keep claims proportional to the evidence you found

## Common Mistakes

- Do not answer from memory when the library has no support
- Do not present inferred trends as if they are direct quotes
- Do not treat example questions from earlier testing as fixed templates
- Do not silently mix external web knowledge into a library-only answer
