import argparse
from pathlib import Path

from guoji_yichan_guancha.library import build_library


SOURCE_DIR = Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取")
OUTPUT_DIR = Path("data/library")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()
    print(build_library(Path(args.source_dir), Path(args.output_dir)))


if __name__ == "__main__":
    main()
