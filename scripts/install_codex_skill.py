import argparse
from pathlib import Path


SKILL_NAME = "guoji-yichan-guancha"


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    template_path = repo_root / "skills" / SKILL_NAME / "SKILL.template.md"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target-dir",
        default=str(Path.home() / ".codex" / "skills" / SKILL_NAME),
    )
    args = parser.parse_args()

    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    rendered = template_path.read_text(encoding="utf-8").replace(
        "__REPO_ROOT__", str(repo_root)
    )
    target_path = target_dir / "SKILL.md"
    target_path.write_text(rendered, encoding="utf-8")

    print(f"Installed {SKILL_NAME} to {target_path}")


if __name__ == "__main__":
    main()
