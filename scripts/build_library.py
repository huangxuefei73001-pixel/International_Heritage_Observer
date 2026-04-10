from pathlib import Path

from guoji_yichan_guancha.library import build_library


SOURCE_DIR = Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取")
OUTPUT_DIR = Path("data/library")


if __name__ == "__main__":
    print(build_library(SOURCE_DIR, OUTPUT_DIR))
