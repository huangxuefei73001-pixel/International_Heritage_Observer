from pathlib import Path
import unittest

from guoji_yichan_guancha.parser import parse_docx_article


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
