from __future__ import annotations

from pathlib import Path

from guoji_yichan_guancha.query import build_answer_bundle


def answer_from_library(
    question: str,
    library_path: Path,
    *,
    strict_source_mode: bool = True,
) -> dict:
    return build_answer_bundle(
        question,
        library_path,
        limit=5,
        strict_source_mode=strict_source_mode,
    )
