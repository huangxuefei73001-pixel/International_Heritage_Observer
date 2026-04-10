from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .library import build_library


def sync_incremental(
    source_dir: Path,
    output_dir: Path,
    log_dir: Path,
    run_at: datetime | None = None,
) -> dict:
    run_at = run_at or datetime.now()
    summary = build_library(source_dir, output_dir)
    summary["source_dir"] = str(source_dir)
    summary["output_dir"] = str(output_dir)
    summary["synced_at"] = run_at.isoformat(timespec="seconds")

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_at.strftime('%Y%m%d-%H%M%S')}.json"
    with log_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    summary["log_path"] = str(log_path)
    return summary
