from pathlib import Path
import unittest

from guoji_yichan_guancha.parser import parse_docx_article, parse_markdown_article


class ParseDocxArticleTest(unittest.TestCase):
    def test_parse_docx_article_reads_metadata_and_falls_back_to_filename(self) -> None:
        fixture = Path("tests/fixtures/sample_article.docx")

        record = parse_docx_article(fixture, category="韩国")

        self.assertEqual(record.title, "sample_article")
        self.assertEqual(record.published_at, "2026-03-20 11:25")
        self.assertEqual(record.category, "韩国")
        self.assertEqual(record.source_url, "https://mp.weixin.qq.com/s/example")
        self.assertIn("世界遗产大会跨部门工作会", record.content_text)
        self.assertEqual(record.parse_status, "title_fallback")


if __name__ == "__main__":
    unittest.main()


class ParseMarkdownArticleTest(unittest.TestCase):
    def test_parse_markdown_article_reads_metadata_and_cleans_body(self) -> None:
        fixture = Path("tests/tmp/sample_article.md")
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(
            "\n".join(
                [
                    "第48届世界遗产大会官方网站上线",
                    "================",
                    "",
                    "原创 国际遗产观察 2026-05-21 20:30 北京",
                    "",
                    "> 原文地址: [https://mp.weixin.qq.com/s/example-md](https://mp.weixin.qq.com/s/example-md)",
                    "",
                    "[第48届世界遗产大会](https://mp.weixin.qq.com/s/foo)",
                    "",
                    "![](https://example.com/image.png)",
                    "",
                    "网站提供参会报名入口、大会概况、论坛和边会信息。",
                    "",
                    "阅读![](data:image/svg+xml,xxxx)",
                ]
            ),
            encoding="utf-8",
        )

        record = parse_markdown_article(fixture, category="未分类")

        self.assertEqual(record.title, "第48届世界遗产大会官方网站上线")
        self.assertEqual(record.published_at, "2026-05-21 20:30")
        self.assertEqual(record.channel, "国际遗产观察")
        self.assertEqual(record.source_url, "https://mp.weixin.qq.com/s/example-md")
        self.assertIn("网站提供参会报名入口", record.content_text)
        self.assertNotIn("阅读![](data:image", record.content_text)
        self.assertEqual(record.parse_status, "ok")
