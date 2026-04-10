from __future__ import annotations

from pathlib import Path

from app.config import Settings
from guoji_yichan_guancha.sync import sync_incremental


def build_sync_paths(settings: Settings) -> tuple[Path, Path, Path]:
    library_jsonl_path = Path(settings.library_path)
    output_dir = library_jsonl_path.parent
    source_dir = Path(settings.incoming_source_dir)
    log_dir = Path(settings.sync_log_dir)
    return source_dir, output_dir, log_dir


def refresh_library(settings: Settings) -> dict:
    source_dir, output_dir, log_dir = build_sync_paths(settings)
    return sync_incremental(source_dir, output_dir, log_dir)
