from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent


def load_polish_system_prompt() -> str:
    return (_PROMPT_DIR / "polish_system.md").read_text(encoding="utf-8")
