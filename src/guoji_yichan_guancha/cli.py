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
