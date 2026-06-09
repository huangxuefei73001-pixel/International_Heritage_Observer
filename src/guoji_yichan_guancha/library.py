from __future__ import annotations

import json
from pathlib import Path

from .parser import parse_docx_article, parse_markdown_article


def _iter_source_files(source_dir: Path) -> list[Path]:
    return sorted(
        [*source_dir.rglob("*.docx"), *source_dir.rglob("*.md")],
        key=lambda path: str(path),
    )


def _parse_article(path: Path, category: str):
    if path.suffix.lower() == ".md":
        return parse_markdown_article(path, category=category)
    return parse_docx_article(path, category=category)


def build_library(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    jsonl_path = output_dir / "articles.jsonl"
    seen_urls: set[str] = set()
    existing_categories: set[str] = set()

    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                document = json.loads(line)
                source_url = document.get("source_url", "")
                if source_url:
                    seen_urls.add(source_url)
                category = document.get("category", "")
                if category:
                    existing_categories.add(category)

    source_paths = _iter_source_files(source_dir)
    for path in source_paths:
        category = path.parent.name if path.parent != source_dir else "未分类"
        record = _parse_article(path, category=category)
        if record.source_url and record.source_url in seen_urls:
            continue
        if record.source_url:
            seen_urls.add(record.source_url)
        records.append(record)

    mode = "a" if jsonl_path.exists() else "w"
    with jsonl_path.open(mode, encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_document(), ensure_ascii=False) + "\n")

    summary = {
        "article_count": len(records),
        "skipped_duplicates": len(source_paths) - len(records),
        "total_article_count": len(seen_urls),
        "categories": sorted(existing_categories | {record.category for record in records}),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    return summary
