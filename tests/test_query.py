from pathlib import Path
from datetime import date
import unittest

from guoji_yichan_guancha.query import answer_question, infer_evidence_type


class QueryTest(unittest.TestCase):
    def test_infer_evidence_type_distinguishes_report_book_and_meeting(self) -> None:
        report = {"title": "【报告】世界遗产影响评估研究", "category": "报告研究", "content_text": ""}
        book = {"title": "【新书】世界遗产导论", "category": "新书书讯", "content_text": ""}
        meeting = {"title": "世界遗产论坛下周召开", "category": "韩国", "content_text": ""}

        self.assertEqual(infer_evidence_type(report), "报告资源")
        self.assertEqual(infer_evidence_type(book), "书刊资讯")
        self.assertEqual(infer_evidence_type(meeting), "会议新闻")

    def test_answer_question_returns_evidence_first_summary(self) -> None:
        library_path = Path("tests/tmp/articles.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/example","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}\n',
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=3)

        self.assertIn("基于库内文章归纳", answer)
        self.assertIn("库内结论：", answer)
        self.assertIn("证据文章：", answer)
        self.assertIn("可直接用于写作的归纳：", answer)
        self.assertIn("证据边界：", answer)
        self.assertIn("[一般动态] [韩国召开第48届世界遗产大会联席工作会](https://mp.weixin.qq.com/s/example)", answer)
        self.assertIn("https://mp.weixin.qq.com/s/example", answer)
        self.assertIn("2026年韩国的世界遗产动态主要集中在", answer)

    def test_answer_question_prioritizes_matching_year_and_category(self) -> None:
        library_path = Path("tests/tmp/articles_ranked.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/korea","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}',
                    '{"article_id":"2","title":"【报告】英国的世界遗产——面向未来的资产","published_at":"2022-06-28 20:30","channel":"国际遗产观察","category":"英国","source_url":"https://mp.weixin.qq.com/s/uk","local_source_path":"/tmp/b.docx","content_text":"英国世界遗产研究报告。","content_html_excerpt":"<p>y</p>","parse_status":"ok","tags_auto":["英国","世界遗产"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=1)

        self.assertIn("韩国召开第48届世界遗产大会联席工作会", answer)
        self.assertNotIn("英国的世界遗产", answer)

    def test_answer_question_refuses_generic_category_only_matches(self) -> None:
        library_path = Path("tests/tmp/articles_insufficient.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            '{"article_id":"1","title":"欧洲数字遗产峰会将于5月召开","published_at":"2026-03-16 20:30","channel":"国际遗产观察","category":"欧洲","source_url":"https://mp.weixin.qq.com/s/europe","local_source_path":"/tmp/a.docx","content_text":"欧洲数字遗产峰会相关信息。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["欧洲","数字化"]}\n',
            encoding="utf-8",
        )

        answer = answer_question("找几个欧洲近年关于过度旅游治理的案例", library_path, limit=5)

        self.assertEqual(answer, "当前库内没有足够材料支持该回答。")

    def test_answer_question_prefers_explicit_object_match_over_folder_only_match(self) -> None:
        library_path = Path("tests/tmp/articles_object_match.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"越南河内世界遗产咨询考察报告发布","published_at":"2025-12-25 20:30","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/hanoi","local_source_path":"/tmp/a.docx","content_text":"越南河内升龙皇城咨询考察报告发布。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产"]}',
                    '{"article_id":"2","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/korea","local_source_path":"/tmp/b.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>y</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=1)

        self.assertIn("韩国召开第48届世界遗产大会联席工作会", answer)
        self.assertNotIn("越南河内世界遗产咨询考察报告发布", answer)

    def test_answer_question_prefers_explicit_year_matches(self) -> None:
        library_path = Path("tests/tmp/articles_year_match.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/2026","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}',
                    '{"article_id":"2","title":"韩国推选釜山为第48届世界遗产大会候选城市","published_at":"2025-07-01 11:01","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/2025","local_source_path":"/tmp/b.docx","content_text":"韩国推选釜山为候选城市。","content_html_excerpt":"<p>y</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=5)

        self.assertIn("韩国召开第48届世界遗产大会联席工作会", answer)
        self.assertNotIn("韩国推选釜山为第48届世界遗产大会候选城市", answer)

    def test_answer_question_formats_multiple_evidence_items(self) -> None:
        library_path = Path("tests/tmp/articles_multi.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/korea1","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}',
                    '{"article_id":"2","title":"韩国国家遗产厅公布2026年度预算","published_at":"2026-01-28 20:30","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/korea2","local_source_path":"/tmp/b.docx","content_text":"国际交流及世界遗产申报预算增长。","content_html_excerpt":"<p>y</p>","parse_status":"ok","tags_auto":["韩国","世界遗产"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=5)

        self.assertIn("- [一般动态] [韩国召开第48届世界遗产大会联席工作会](https://mp.weixin.qq.com/s/korea1) | 2026-03-20 11:25 | 韩国 | https://mp.weixin.qq.com/s/korea1", answer)
        self.assertIn("- [政策动态] [韩国国家遗产厅公布2026年度预算](https://mp.weixin.qq.com/s/korea2) | 2026-01-28 20:30 | 韩国 | https://mp.weixin.qq.com/s/korea2", answer)
        self.assertIn("- 2026年韩国的世界遗产动态主要集中在", answer)
        self.assertIn("证据边界：", answer)

    def test_answer_question_formats_title_as_clickable_markdown_link(self) -> None:
        library_path = Path("tests/tmp/articles_linked_titles.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/example-link","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}\n',
            encoding="utf-8",
        )

        answer = answer_question("2026年韩国的世界遗产动态有什么？", library_path, limit=1)

        self.assertIn("[韩国召开第48届世界遗产大会联席工作会](https://mp.weixin.qq.com/s/example-link)", answer)

    def test_concept_question_prefers_report_resource_over_meeting_news(self) -> None:
        library_path = Path("tests/tmp/articles_concept.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"【报告】突出普遍价值与遗产阐释研究","published_at":"2024-03-01 20:30","channel":"国际遗产观察","category":"报告研究","source_url":"https://mp.weixin.qq.com/s/report","local_source_path":"/tmp/a.docx","content_text":"报告系统讨论突出普遍价值的定义、边界与阐释。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["突出普遍价值"]}',
                    '{"article_id":"2","title":"突出普遍价值国际论坛将在首尔举行","published_at":"2024-03-02 20:30","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/forum","local_source_path":"/tmp/b.docx","content_text":"会议将讨论突出普遍价值议题。","content_html_excerpt":"<p>y</p>","parse_status":"ok","tags_auto":["突出普遍价值"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question("突出普遍价值怎么界定？", library_path, limit=1)

        self.assertIn("【报告】突出普遍价值与遗产阐释研究", answer)
        self.assertNotIn("国际论坛将在首尔举行", answer)

    def test_trend_question_respects_recent_three_year_window(self) -> None:
        library_path = Path("tests/tmp/articles_recent_trend.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"UNESCO举办阿拉伯地区世界遗产数字记录工作坊","published_at":"2023-03-14 20:30","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/a","local_source_path":"/tmp/a.docx","content_text":"世界遗产数字记录工作坊。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["世界遗产","数字化"]}',
                    '{"article_id":"2","title":"【手册】沙特文化部《文化遗产记录与数字存档指南》","published_at":"2022-07-11 20:30","channel":"国际遗产观察","category":"阿拉伯","source_url":"https://mp.weixin.qq.com/s/b","local_source_path":"/tmp/b.docx","content_text":"文化遗产记录与数字存档指南。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["数字化"]}',
                    '{"article_id":"3","title":"世界遗产数字平台建设指南","published_at":"2025-02-01 20:30","channel":"国际遗产观察","category":"报告研究","source_url":"https://mp.weixin.qq.com/s/c","local_source_path":"/tmp/c.docx","content_text":"数字平台、数据库与标准。","content_html_excerpt":"<p>c</p>","parse_status":"ok","tags_auto":["数字平台"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "世界遗产数字化在国际上有什么发展？近三年的时间范围内。",
            library_path,
            limit=5,
            reference_date=date(2026, 4, 9),
        )

        self.assertIn("UNESCO举办阿拉伯地区世界遗产数字记录工作坊", answer)
        self.assertIn("世界遗产数字平台建设指南", answer)
        self.assertNotIn("文化遗产记录与数字存档指南", answer)

    def test_trend_question_prefers_substantive_digital_development_over_generic_event(self) -> None:
        library_path = Path("tests/tmp/articles_digital_trend_quality.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"第47届世界遗产大会青年论坛7月举行","published_at":"2025-04-03 08:30","channel":"国际遗产观察","category":"世界遗产大会","source_url":"https://mp.weixin.qq.com/s/event","local_source_path":"/tmp/a.docx","content_text":"青年论坛活动通知。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["世界遗产大会"]}',
                    '{"article_id":"2","title":"世界遗产数字平台建设指南","published_at":"2025-02-01 20:30","channel":"国际遗产观察","category":"报告研究","source_url":"https://mp.weixin.qq.com/s/guide","local_source_path":"/tmp/b.docx","content_text":"数字平台、数据库、三维记录与标准。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["数字平台"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "世界遗产数字化在国际上有什么发展？近三年的时间范围内。",
            library_path,
            limit=1,
            reference_date=date(2026, 4, 9),
        )

        self.assertIn("世界遗产数字平台建设指南", answer)
        self.assertNotIn("青年论坛7月举行", answer)

    def test_digital_trend_question_filters_out_non_digital_world_heritage_event(self) -> None:
        library_path = Path("tests/tmp/articles_digital_focus.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"第47届世界遗产大会青年论坛7月举行","published_at":"2025-04-03 08:30","channel":"国际遗产观察","category":"世界遗产大会","source_url":"https://mp.weixin.qq.com/s/event","local_source_path":"/tmp/a.docx","content_text":"青年论坛活动通知。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["世界遗产大会"]}',
                    '{"article_id":"2","title":"UNESCO举办阿拉伯地区世界遗产数字记录工作坊","published_at":"2023-03-14 20:30","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/digital","local_source_path":"/tmp/b.docx","content_text":"世界遗产数字记录工作坊。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["世界遗产","数字化"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "世界遗产数字化在国际上有什么发展？近三年的时间范围内。",
            library_path,
            limit=2,
            reference_date=date(2026, 4, 9),
        )

        self.assertIn("UNESCO举办阿拉伯地区世界遗产数字记录工作坊", answer)
        self.assertNotIn("青年论坛7月举行", answer)

    def test_digital_trend_question_can_include_broader_heritage_digital_materials(self) -> None:
        library_path = Path("tests/tmp/articles_broader_digital_scope.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"联合国教科文组织数字遗产政策","published_at":"2024-05-10 20:30","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/policy","local_source_path":"/tmp/a.docx","content_text":"文章探讨数字技术对遗产保护途径的影响，以及数字信息长期保存的挑战。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["数字遗产"]}',
                    '{"article_id":"2","title":"文化遗产数字化战略","published_at":"2025-06-01 20:30","channel":"国际遗产观察","category":"报告研究","source_url":"https://mp.weixin.qq.com/s/strategy","local_source_path":"/tmp/b.docx","content_text":"该文描述实现文化遗产数字化的方法论，特别是如何构建虚拟世界以展示文化遗产。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["数字化"]}',
                    '{"article_id":"3","title":"第47届世界遗产大会青年论坛7月举行","published_at":"2025-04-03 08:30","channel":"国际遗产观察","category":"世界遗产大会","source_url":"https://mp.weixin.qq.com/s/event","local_source_path":"/tmp/c.docx","content_text":"青年论坛活动通知。","content_html_excerpt":"<p>c</p>","parse_status":"ok","tags_auto":["世界遗产大会"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "世界遗产数字化在国际上有什么发展？近三年的时间范围内。",
            library_path,
            limit=5,
            reference_date=date(2026, 4, 9),
        )

        self.assertIn("联合国教科文组织数字遗产政策", answer)
        self.assertIn("文化遗产数字化战略", answer)
        self.assertNotIn("青年论坛7月举行", answer)

    def test_digital_trend_question_keeps_semantically_related_materials(self) -> None:
        library_path = Path("tests/tmp/articles_semantic_digital_scope.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"英国发布数字文化遗产创新报告","published_at":"2025-06-20 20:31","channel":"国际遗产观察","category":"英国","source_url":"https://mp.weixin.qq.com/s/uk-digital","local_source_path":"/tmp/a.docx","content_text":"报告讨论数字化采集、建模、平台与遗产创新应用。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["数字化"]}',
                    '{"article_id":"2","title":"欧洲文化遗产数字化门户2025会议6月在波兰召开","published_at":"2025-02-13 20:30","channel":"国际遗产观察","category":"欧洲","source_url":"https://mp.weixin.qq.com/s/eu-portal","local_source_path":"/tmp/b.docx","content_text":"会议关注文化遗产数字化门户、平台建设和跨国协作。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["数字平台"]}',
                    '{"article_id":"3","title":"世界遗产大会秘书处发布青年志愿者招募通知","published_at":"2025-04-03 08:30","channel":"国际遗产观察","category":"世界遗产大会","source_url":"https://mp.weixin.qq.com/s/event","local_source_path":"/tmp/c.docx","content_text":"志愿者招募通知。","content_html_excerpt":"<p>c</p>","parse_status":"ok","tags_auto":["世界遗产大会"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "世界遗产数字化在国际上有什么发展？近三年的时间范围内。",
            library_path,
            limit=5,
            reference_date=date(2026, 4, 9),
        )

        self.assertIn("英国发布数字文化遗产创新报告", answer)
        self.assertIn("欧洲文化遗产数字化门户2025会议6月在波兰召开", answer)
        self.assertNotIn("青年志愿者招募通知", answer)


if __name__ == "__main__":
    unittest.main()
