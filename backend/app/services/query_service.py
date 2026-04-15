from __future__ import annotations

from pathlib import Path

from guoji_yichan_guancha.query import build_answer_bundle


def answer_from_library(question: str, library_path: Path) -> dict:
    return build_answer_bundle(question, library_path, limit=5)
