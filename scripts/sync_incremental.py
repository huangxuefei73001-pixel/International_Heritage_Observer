import argparse
from pathlib import Path

from guoji_yichan_guancha.sync import sync_incremental


DEFAULT_SOURCE_DIR = Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增")
DEFAULT_OUTPUT_DIR = Path("data/library")
DEFAULT_LOG_DIR = Path("data/sync_logs")
DEFAULT_ARCHIVE_DIR = DEFAULT_SOURCE_DIR.parent / "已同步归档"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR))
    args = parser.parse_args()
    summary = sync_incremental(
        Path(args.source_dir),
        Path(args.output_dir),
        Path(args.log_dir),
        Path(args.archive_dir),
    )
    print(summary)


if __name__ == "__main__":
    main()
