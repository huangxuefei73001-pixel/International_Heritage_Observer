from __future__ import annotations

import json
from pathlib import Path

from .parser import parse_docx_article


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

    for path in sorted(source_dir.rglob("*.docx")):
        category = path.parent.name if path.parent != source_dir else "未分类"
        record = parse_docx_article(path, category=category)
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
        "skipped_duplicates": len(list(source_dir.rglob("*.docx"))) - len(records),
        "total_article_count": len(seen_urls),
        "categories": sorted(existing_categories | {record.category for record in records}),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    return summary
