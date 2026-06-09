import unittest
from datetime import datetime
import importlib.util
from pathlib import Path
import shutil

from guoji_yichan_guancha.models import ArticleRecord
from guoji_yichan_guancha.library import build_library
from guoji_yichan_guancha.sync import sync_incremental


class ArticleRecordTest(unittest.TestCase):
    def test_article_record_to_document_uses_required_fields(self) -> None:
        record = ArticleRecord(
            article_id="abc123",
            title="韩国召开第48届世界遗产大会联席工作会",
            published_at="2026-03-20 11:25",
            channel="国际遗产观察",
            category="韩国",
            source_url="https://mp.weixin.qq.com/s/abamHniN0MaGiOCA54LIOQ",
            local_source_path="/tmp/sample.docx",
            content_text="韩国日前召开第48届世界遗产大会跨部门工作会。",
            content_html_excerpt="<p>韩国日前召开第48届世界遗产大会跨部门工作会。</p>",
            parse_status="ok",
            tags_auto=["韩国", "世界遗产大会"],
        )

        document = record.to_document()

        self.assertEqual(document["article_id"], "abc123")
        self.assertTrue(document["title"].startswith("韩国召开"))
        self.assertEqual(document["category"], "韩国")
        self.assertEqual(document["tags_auto"], ["韩国", "世界遗产大会"])


class BuildLibraryTest(unittest.TestCase):
    def test_build_library_writes_jsonl_and_summary(self) -> None:
        source_dir = Path("tests/fixtures")
        output_dir = Path("tests/tmp/library")

        if output_dir.exists():
            for path in sorted(output_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

        result = build_library(source_dir, output_dir)

        self.assertEqual(result["article_count"], 1)
        self.assertTrue((output_dir / "articles.jsonl").exists())
        self.assertTrue((output_dir / "summary.json").exists())

    def test_build_library_skips_existing_source_urls(self) -> None:
        source_dir = Path("tests/fixtures")
        output_dir = Path("tests/tmp/library-duplicates")

        if output_dir.exists():
            for path in sorted(output_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

        first = build_library(source_dir, output_dir)
        second = build_library(source_dir, output_dir)

        self.assertEqual(first["article_count"], 1)
        self.assertEqual(second["article_count"], 0)
        self.assertEqual(second["skipped_duplicates"], 1)
        self.assertEqual(second["total_article_count"], 1)

    def test_build_library_reads_markdown_articles(self) -> None:
        source_dir = Path("tests/tmp/library-md-source")
        output_dir = Path("tests/tmp/library-md-output")

        for target in (source_dir, output_dir):
            if target.exists():
                for path in sorted(target.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()

        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "sample.md").write_text(
            "\n".join(
                [
                    "奈文研石垣BIM遗产信息系统研究",
                    "================",
                    "",
                    "原创 国际遗产观察 2026-05-20 20:30 北京",
                    "",
                    "> 原文地址: [https://mp.weixin.qq.com/s/sample-md](https://mp.weixin.qq.com/s/sample-md)",
                    "",
                    "BIM、数字、信息系统、数据。",
                ]
            ),
            encoding="utf-8",
        )

        result = build_library(source_dir, output_dir)

        self.assertEqual(result["article_count"], 1)
        self.assertEqual(result["skipped_duplicates"], 0)
        self.assertIn("未分类", result["categories"])
        articles = (output_dir / "articles.jsonl").read_text(encoding="utf-8")
        self.assertIn("奈文研石垣BIM遗产信息系统研究", articles)

    def test_sync_incremental_writes_run_log(self) -> None:
        fixture_dir = Path("tests/fixtures")
        source_dir = Path("tests/tmp/sync-source")
        output_dir = Path("tests/tmp/library-sync")
        log_dir = Path("tests/tmp/sync-logs")
        archive_dir = Path("tests/tmp/sync-archive")

        for target in (source_dir, output_dir, log_dir, archive_dir):
            if target.exists():
                for path in sorted(target.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()
        source_dir.mkdir(parents=True, exist_ok=True)
        for path in fixture_dir.glob("*.docx"):
            shutil.copy2(path, source_dir / path.name)

        result = sync_incremental(
            source_dir,
            output_dir,
            log_dir,
            archive_dir,
            run_at=datetime(2026, 4, 9, 15, 30, 0),
        )

        self.assertEqual(result["article_count"], 1)
        self.assertTrue((output_dir / "articles.jsonl").exists())
        self.assertTrue((log_dir / "20260409-153000.json").exists())
        self.assertEqual(result["log_path"], str(log_dir / "20260409-153000.json"))
        self.assertEqual(result["archive_dir"], str(archive_dir))
        self.assertEqual(result["moved_source_files"], 1)
        self.assertTrue((archive_dir / "20260409-153000" / "sample_article.docx").exists())
        self.assertEqual(len(list(source_dir.glob("*.docx"))), 0)

    def test_sync_incremental_moves_markdown_files_to_archive(self) -> None:
        source_dir = Path("tests/tmp/sync-md-source")
        output_dir = Path("tests/tmp/library-sync-md")
        log_dir = Path("tests/tmp/sync-md-logs")
        archive_dir = Path("tests/tmp/sync-md-archive")

        for target in (source_dir, output_dir, log_dir, archive_dir):
            if target.exists():
                for path in sorted(target.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()

        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "sample.md").write_text(
            "\n".join(
                [
                    "第四届欧洲数字叙事节即将启动",
                    "================",
                    "",
                    "原创 国际遗产观察 2026-05-12 20:30 北京",
                    "",
                    "> 原文地址: [https://mp.weixin.qq.com/s/sample-sync-md](https://mp.weixin.qq.com/s/sample-sync-md)",
                    "",
                    "数字叙事、平台、展示。",
                ]
            ),
            encoding="utf-8",
        )

        result = sync_incremental(
            source_dir,
            output_dir,
            log_dir,
            archive_dir,
            run_at=datetime(2026, 6, 9, 10, 0, 0),
        )

        self.assertEqual(result["article_count"], 1)
        self.assertEqual(result["moved_source_files"], 1)
        self.assertTrue((archive_dir / "20260609-100000" / "sample.md").exists())
        self.assertEqual(len(list(source_dir.glob("*.md"))), 0)

    def test_sync_script_defaults_to_benci_xinzeng_directory(self) -> None:
        script_path = Path("scripts/sync_incremental.py")
        spec = importlib.util.spec_from_file_location("sync_incremental_script", script_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        self.assertEqual(
            module.DEFAULT_SOURCE_DIR,
            Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增"),
        )
        self.assertEqual(
            module.DEFAULT_ARCHIVE_DIR,
            Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/已同步归档"),
        )


if __name__ == "__main__":
    unittest.main()
