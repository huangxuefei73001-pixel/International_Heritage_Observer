from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil

from .library import build_library


def _archive_source_batch(source_dir: Path, archive_dir: Path, run_at: datetime) -> int:
    source_paths = sorted(
        [*source_dir.rglob("*.docx"), *source_dir.rglob("*.md")],
        key=lambda path: str(path),
    )
    if not source_paths:
        return 0

    batch_dir = archive_dir / run_at.strftime("%Y%m%d-%H%M%S")
    moved_count = 0
    for path in source_paths:
        relative_path = path.relative_to(source_dir)
        target_path = batch_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target_path))
        moved_count += 1

    for directory in sorted(source_dir.rglob("*"), reverse=True):
        if directory.is_dir() and directory != source_dir:
            try:
                directory.rmdir()
            except OSError:
                pass

    return moved_count


def sync_incremental(
    source_dir: Path,
    output_dir: Path,
    log_dir: Path,
    archive_dir: Path | None = None,
    run_at: datetime | None = None,
) -> dict:
    run_at = run_at or datetime.now()
    summary = build_library(source_dir, output_dir)
    archive_dir = archive_dir or source_dir.parent / "已同步归档"
    moved_count = _archive_source_batch(source_dir, archive_dir, run_at)
    summary["source_dir"] = str(source_dir)
    summary["output_dir"] = str(output_dir)
    summary["archive_dir"] = str(archive_dir)
    summary["moved_source_files"] = moved_count
    summary["synced_at"] = run_at.isoformat(timespec="seconds")

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_at.strftime('%Y%m%d-%H%M%S')}.json"
    with log_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    summary["log_path"] = str(log_path)
    return summary
