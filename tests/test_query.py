from pathlib import Path
from datetime import date
import unittest
from unittest.mock import patch

from guoji_yichan_guancha.query import (
    _analyze_question,
    _fetch_unesco_records_paginated,
    _select_answer_context,
    _select_unesco_mode,
    _matches_registry_site_name,
    _filter_unesco_world_heritage_sites,
    answer_question,
    detect_document_source_type,
    infer_evidence_type,
    is_document_from_allowed_source,
)


class QueryTest(unittest.TestCase):
    def test_source_whitelist_accepts_only_kb_and_unesco_api(self) -> None:
        kb_document = {"channel": "国际遗产观察"}
        unesco_document = {"source_system": "whc001"}
        foreign_document = {"channel": "外部资料库", "source_system": "other"}

        self.assertEqual(detect_document_source_type(kb_document), "KB")
        self.assertEqual(detect_document_source_type(unesco_document), "UNESCO_API")
        self.assertIsNone(detect_document_source_type(foreign_document))
        self.assertTrue(is_document_from_allowed_source(kb_document))
        self.assertTrue(is_document_from_allowed_source(unesco_document))
        self.assertFalse(is_document_from_allowed_source(foreign_document))

    def test_mode_selection_prefers_registry_for_explicit_site_lookup(self) -> None:
        question = "威尼斯及其泻湖的风险治理与列入年份是什么？"
        analysis = _analyze_question(question, [], date(2026, 4, 23))
        self.assertEqual(_select_unesco_mode(question, analysis), "registry_query")

    def test_mode_selection_keeps_thematic_for_country_scoped_theme_case_query(self) -> None:
        question = "意大利有哪些与灾害风险相关的世界遗产地案例？"
        analysis = _analyze_question(question, [], date(2026, 4, 23))
        self.assertEqual(_select_unesco_mode(question, analysis), "thematic_case")

    def test_mode_selection_keeps_practice_case_queries_in_kb(self) -> None:
        question = "有什么数字化技术支持遗产地或博物馆展示的案例？"
        analysis = _analyze_question(question, [], date(2026, 4, 29))
        self.assertIsNone(_select_unesco_mode(question, analysis))

    def test_mode_selection_uses_registry_for_site_year_lookup(self) -> None:
        question = "长城哪一年列入世界遗产？"
        analysis = _analyze_question(question, [], date(2026, 4, 29))
        self.assertEqual(_select_unesco_mode(question, analysis), "registry_query")

    def test_registry_site_name_matching_supports_partial_and_fuzzy_variants(self) -> None:
        record = {"name_zh": "威尼斯及泻湖", "name_en": "Venice and its Lagoon"}
        self.assertTrue(_matches_registry_site_name(record, "威尼斯"))
        self.assertTrue(_matches_registry_site_name(record, "威尼斯及其泻湖"))
        self.assertTrue(_matches_registry_site_name(record, "Venice"))

    @patch("guoji_yichan_guancha.query._fetch_unesco_records")
    def test_collection_registry_query_fetches_multiple_pages(self, mock_fetch_records) -> None:
        first_page = [
            {
                "id_no": index,
                "name_zh": f"站点{index}",
                "name_en": f"Site {index}",
                "states_names": ["Italy"],
                "date_inscribed": 1980 + index,
                "category": "Cultural",
            }
            for index in range(1, 101)
        ]
        second_page = [
            {
                "id_no": index,
                "name_zh": f"站点{index}",
                "name_en": f"Site {index}",
                "states_names": ["Italy"],
                "date_inscribed": 1980 + index,
                "category": "Cultural",
            }
            for index in range(101, 106)
        ]
        mock_fetch_records.side_effect = [first_page, second_page]

        records = _fetch_unesco_records_paginated({"where": 'states_names like "Italy"'})

        self.assertEqual(len(records), 105)
        self.assertEqual(mock_fetch_records.call_count, 2)

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
        self.assertIn("如果压缩成一句判断：", answer)
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

        self.assertIn("- [一般动态] [韩国召开第48届世界遗产大会联席工作会](https://mp.weixin.qq.com/s/korea1) | 2026-03-20 11:25 | 韩国", answer)
        self.assertIn("- [政策动态] [韩国国家遗产厅公布2026年度预算](https://mp.weixin.qq.com/s/korea2) | 2026-01-28 20:30 | 韩国", answer)
        self.assertIn("如果压缩成一句判断：", answer)
        self.assertIn("证据边界：", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_question_understanding_keeps_resilience_and_disaster_governance_as_primary_theme(self, mock_search) -> None:
        mock_search.return_value = [
            {
                "site_name": "威尼斯及其泻湖",
                "country": "意大利",
                "inscription_year": 1987,
                "unesco_url": "https://whc.unesco.org/en/list/394",
                "matched_terms": ["climate", "risk"],
            }
        ]
        library_path = Path("tests/tmp/articles_resilience_case_carrier.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"UNESCO发布世界遗产城市灾害风险治理案例集","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/resilience-1","local_source_path":"/tmp/a.docx","content_text":"文章讨论城市韧性、灾害治理与世界遗产地案例之间的关系。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害治理","世界遗产"]}',
                    '{"article_id":"2","title":"历史城区韧性提升与灾害治理国际培训总结","published_at":"2024-08-01 20:30","channel":"国际遗产观察","category":"会议新闻","source_url":"https://mp.weixin.qq.com/s/resilience-2","local_source_path":"/tmp/b.docx","content_text":"该文梳理历史城区和世界遗产地如何把灾害风险治理纳入韧性框架。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )

        self.assertIn("城市韧性与灾害治理", answer)
        self.assertIn("把世界遗产地作为案例载体", answer)
        self.assertNotIn("与“世界遗产案例”直接相关的代表性做法", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageRegistry")
    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_thematic_mode_keeps_existing_unesco_case_path(self, mock_thematic_search, mock_registry_search) -> None:
        mock_thematic_search.return_value = []
        library_path = Path("tests/tmp/articles_thematic_mode.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            '{"article_id":"1","title":"世界遗产城市韧性与灾害风险治理框架发布","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-kb","local_source_path":"/tmp/a.docx","content_text":"文章系统讨论城市韧性、灾害风险、风险治理与世界遗产城市管理框架。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理","世界遗产"]}\n',
            encoding="utf-8",
        )

        answer_question("我需要找城市韧性与灾害治理的信息，包括世界遗产地案例", library_path, limit=5)

        mock_thematic_search.assert_called_once()
        mock_registry_search.assert_not_called()

    @patch("guoji_yichan_guancha.query.searchWorldHeritageRegistry")
    def test_registry_mode_answers_entity_attribute_query(self, mock_registry_search) -> None:
        mock_registry_search.return_value = [
            {
                "site_name": "威尼斯及其泻湖",
                "country": "意大利",
                "inscription_year": 1987,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/394",
                "description": "Example description.",
            }
        ]
        library_path = Path("tests/tmp/articles_registry_entity.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text("", encoding="utf-8")

        answer = answer_question("威尼斯及其泻湖的列入年份是什么？", library_path, limit=5)

        mock_registry_search.assert_called_once()
        self.assertIn("UNESCO 世界遗产名录信息：", answer)
        self.assertIn("威尼斯及其泻湖的列入年份：1987", answer)
        self.assertNotIn("基于库内文章归纳", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageRegistry")
    def test_registry_mode_answers_collection_query(self, mock_registry_search) -> None:
        mock_registry_search.return_value = [
            {
                "site_name": "威尼斯及其泻湖",
                "country": "意大利",
                "inscription_year": 1987,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/394",
                "description": "",
            },
            {
                "site_name": "罗马历史中心",
                "country": "意大利",
                "inscription_year": 1980,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/91",
                "description": "",
            },
        ]
        library_path = Path("tests/tmp/articles_registry_collection.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text("", encoding="utf-8")

        answer = answer_question("意大利有哪些世界遗产地？", library_path, limit=5)

        self.assertIn("检索范围：意大利世界遗产地", answer)
        self.assertIn("威尼斯及其泻湖", answer)
        self.assertIn("罗马历史中心", answer)
        self.assertIn("共2处", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageRegistry")
    def test_registry_mode_answers_country_count_query_with_total_and_full_list(self, mock_registry_search) -> None:
        mock_registry_search.return_value = [
            {
                "site_name": "长城",
                "country": "中国",
                "inscription_year": 1987,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/438",
                "description": "",
            },
            {
                "site_name": "明清故宫",
                "country": "中国",
                "inscription_year": 1987,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/439",
                "description": "",
            },
            {
                "site_name": "莫高窟",
                "country": "中国",
                "inscription_year": 1987,
                "heritage_type": "cultural",
                "unesco_url": "https://whc.unesco.org/en/list/440",
                "description": "",
            },
        ]
        library_path = Path("tests/tmp/articles_registry_count.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text("", encoding="utf-8")

        answer = answer_question("中国一共有多少处世界遗产地？", library_path, limit=5)

        mock_registry_search.assert_called_once()
        self.assertIn("UNESCO 世界遗产名录信息：", answer)
        self.assertIn("中国世界遗产地数量：3处", answer)
        self.assertIn("检索范围：中国世界遗产地（共3处）", answer)
        self.assertIn("长城", answer)
        self.assertIn("明清故宫", answer)
        self.assertIn("莫高窟", answer)
        self.assertNotIn("基于库内文章归纳", answer)

    @patch("guoji_yichan_guancha.query._fetch_unesco_records")
    def test_registry_search_filters_by_structured_fields(self, mock_fetch_records) -> None:
        mock_fetch_records.return_value = [
            {
                "id_no": 394,
                "name_zh": "威尼斯及其泻湖",
                "name_en": "Venice and its Lagoon",
                "states_names": ["Italy"],
                "date_inscribed": 1987,
                "category": "Cultural",
            },
            {
                "id_no": 91,
                "name_zh": "罗马历史中心",
                "name_en": "Historic Centre of Rome",
                "states_names": ["Italy"],
                "date_inscribed": 1980,
                "category": "Cultural",
            },
        ]

        from guoji_yichan_guancha.query import searchWorldHeritageRegistry

        matches = searchWorldHeritageRegistry(
            {
                "mode": "collection_query",
                "site_name": None,
                "country": "Italy",
                "heritage_type": "cultural",
                "inscription_year": "1987",
                "asks_fields": {},
                "general_examples": False,
            }
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["site_name"], "威尼斯及其泻湖")

    def test_registry_fetch_params_prefer_structured_where_filters(self) -> None:
        from guoji_yichan_guancha.query import _build_registry_fetch_params

        site_requests = _build_registry_fetch_params(
            {
                "mode": "entity_lookup",
                "site_name": "威尼斯及其泻湖",
                "country": None,
                "heritage_type": None,
                "inscription_year": None,
                "asks_fields": {"year": True},
                "general_examples": False,
            }
        )
        self.assertTrue(any("where" in request and "name_zh like" in request["where"] for request in site_requests))

        collection_requests = _build_registry_fetch_params(
            {
                "mode": "collection_query",
                "site_name": None,
                "country": "意大利",
                "heritage_type": "cultural",
                "inscription_year": None,
                "asks_fields": {},
                "general_examples": True,
            }
        )
        self.assertTrue(any('states_names like "Italy"' in request.get("where", "") for request in collection_requests))
        self.assertTrue(any('category = "Cultural"' in request.get("where", "") for request in collection_requests))

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_theme_led_query_prioritizes_resilience_and_uses_evidence_derived_headings(self, mock_search) -> None:
        mock_search.return_value = [
            {
                "site_name": "威尼斯及其泻湖",
                "country": "意大利",
                "inscription_year": 1987,
                "unesco_url": "https://whc.unesco.org/en/list/394",
                "matched_terms": ["climate", "risk"],
            },
            {
                "site_name": "巴米扬山谷的文化景观和考古遗迹",
                "country": "阿富汗",
                "inscription_year": 2003,
                "unesco_url": "https://whc.unesco.org/en/list/208",
                "matched_terms": ["disaster", "risk"],
            },
        ]
        library_path = Path("tests/tmp/articles_theme_led_query.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"UNESCO同世界旅游组织UNWTO加强合作","published_at":"2026-03-21 11:25","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/generic-1","local_source_path":"/tmp/a.docx","content_text":"推动全球可持续、包容和有韧性的旅游，并涉及世界遗产合作。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["世界遗产"]}',
                    '{"article_id":"2","title":"埃及世界遗产地卢克索发现完整古罗马城市和鸽子塔遗址","published_at":"2023-01-28 20:30","channel":"国际遗产观察","category":"非洲","source_url":"https://mp.weixin.qq.com/s/generic-2","local_source_path":"/tmp/b.docx","content_text":"这是一条世界遗产地一般动态。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["世界遗产地"]}',
                    '{"article_id":"3","title":"世界遗产城市韧性与灾害风险治理框架发布","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-1","local_source_path":"/tmp/c.docx","content_text":"文章系统讨论城市韧性、灾害风险、风险治理与世界遗产城市管理框架。","content_html_excerpt":"<p>c</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理","世界遗产"]}',
                    '{"article_id":"4","title":"历史城区灾害应急保护与恢复机制研究","published_at":"2024-08-01 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/theme-2","local_source_path":"/tmp/d.docx","content_text":"聚焦灾害、应急、恢复和世界遗产地保护机制。","content_html_excerpt":"<p>d</p>","parse_status":"ok","tags_auto":["灾害","应急","恢复"]}',
                    '{"article_id":"5","title":"气候风险下的遗产地脆弱性评估与恢复路径","published_at":"2024-05-12 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-3","local_source_path":"/tmp/e.docx","content_text":"围绕风险、脆弱性、恢复和治理提出遗产地案例。","content_html_excerpt":"<p>e</p>","parse_status":"ok","tags_auto":["风险","脆弱性","恢复"]}',
                    '{"article_id":"6","title":"世界遗产地防灾与风险管理案例汇编","published_at":"2023-11-06 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-4","local_source_path":"/tmp/f.docx","content_text":"介绍防灾、灾害治理、风险管理和多个世界遗产地案例。","content_html_excerpt":"<p>f</p>","parse_status":"ok","tags_auto":["防灾","风险管理","世界遗产地"]}',
                    '{"article_id":"7","title":"城市遗产地图集更新","published_at":"2024-02-13 20:30","channel":"国际遗产观察","category":"UNESCO","source_url":"https://mp.weixin.qq.com/s/generic-3","local_source_path":"/tmp/g.docx","content_text":"介绍城市遗产地图平台。","content_html_excerpt":"<p>g</p>","parse_status":"ok","tags_auto":["城市遗产"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        context = _select_answer_context(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )
        top_titles = [document["title"] for document in context["matches"]]
        extended_titles = [document["title"] for document in context["extended_matches"]]

        self.assertIn("世界遗产城市韧性与灾害风险治理框架发布", top_titles[:3])
        self.assertIn("历史城区灾害应急保护与恢复机制研究", top_titles[:4])
        self.assertNotIn("UNESCO同世界旅游组织UNWTO加强合作", top_titles[:3])
        self.assertGreater(len(extended_titles), len(top_titles))

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )

        self.assertIn("城市韧性与风险治理：", answer)
        self.assertIn("灾害应对与应急保护：", answer)
        self.assertIn("脆弱性与恢复机制：", answer)
        self.assertNotIn("国际治理与规则：", answer)
        self.assertNotIn("培训与能力建设：", answer)
        self.assertNotIn("规划与管理工具：", answer)
        self.assertNotIn("5条库内线索", answer)
        self.assertNotIn("条库内线索", answer)

    def test_theme_led_query_prefers_theme_plus_heritage_cases_in_core_selection(self) -> None:
        library_path = Path("tests/tmp/articles_theme_heritage_constraint.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"城市韧性与灾害风险治理框架综述","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-only","local_source_path":"/tmp/a.docx","content_text":"系统讨论城市韧性、灾害风险、治理和恢复框架。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理"]}',
                    '{"article_id":"2","title":"世界遗产地防灾与风险管理案例汇编","published_at":"2024-06-01 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-case","local_source_path":"/tmp/b.docx","content_text":"介绍世界遗产地、防灾、风险管理与灾害治理案例。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["世界遗产地","防灾","风险管理"]}',
                    '{"article_id":"3","title":"历史城区灾害应急保护与恢复机制研究","published_at":"2024-05-12 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/theme-case-2","local_source_path":"/tmp/c.docx","content_text":"聚焦灾害、应急、恢复和世界遗产地保护机制。","content_html_excerpt":"<p>c</p>","parse_status":"ok","tags_auto":["灾害","应急","恢复","世界遗产地"]}',
                ])
            + "\n",
            encoding="utf-8",
        )

        context = _select_answer_context(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=2,
        )
        top_titles = [document["title"] for document in context["matches"]]

        self.assertEqual(top_titles[0], "世界遗产地防灾与风险管理案例汇编")
        self.assertIn("历史城区灾害应急保护与恢复机制研究", top_titles)
        self.assertNotIn("城市韧性与灾害风险治理框架综述", top_titles)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_theme_led_query_without_heritage_cases_returns_clarification_question(self, mock_search) -> None:
        mock_search.return_value = []
        library_path = Path("tests/tmp/articles_theme_no_cases.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"城市韧性与灾害风险治理框架综述","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-only-1","local_source_path":"/tmp/a.docx","content_text":"系统讨论城市韧性、灾害风险、治理和恢复框架。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理"]}',
                    '{"article_id":"2","title":"历史城区灾害应急保护与恢复机制研究","published_at":"2024-05-12 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/theme-only-2","local_source_path":"/tmp/b.docx","content_text":"聚焦灾害、应急、恢复和保护机制。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["灾害","应急","恢复"]}',
                ])
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )

        self.assertIn("当前在UNESCO数据中未检索到与该主题直接匹配的世界遗产地案例。", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_theme_led_query_appends_unesco_cases_when_search_returns_results(self, mock_search) -> None:
        mock_search.return_value = [
            {
                "site_name": "威尼斯及其泻湖",
                "country": "意大利",
                "inscription_year": 1987,
                "unesco_url": "https://whc.unesco.org/en/list/394",
                "matched_terms": ["climate", "risk"],
            },
            {
                "site_name": "巴米扬山谷的文化景观和考古遗迹",
                "country": "阿富汗",
                "inscription_year": 2003,
                "unesco_url": "https://whc.unesco.org/en/list/208",
                "matched_terms": ["disaster", "risk"],
            },
        ]
        library_path = Path("tests/tmp/articles_theme_with_unesco_append.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"世界遗产城市韧性与灾害风险治理框架发布","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-kb-1","local_source_path":"/tmp/a.docx","content_text":"文章系统讨论城市韧性、灾害风险、风险治理与世界遗产城市管理框架。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理","世界遗产"]}',
                    '{"article_id":"2","title":"历史城区灾害应急保护与恢复机制研究","published_at":"2024-08-01 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/theme-kb-2","local_source_path":"/tmp/b.docx","content_text":"聚焦灾害、应急、恢复和世界遗产地保护机制。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["灾害","应急","恢复","世界遗产地"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )

        mock_search.assert_called_once()
        self.assertIn("相关世界遗产地案例（UNESCO）：", answer)
        self.assertIn("威尼斯及其泻湖", answer)
        self.assertIn("意大利", answer)
        self.assertIn("巴米扬山谷的文化景观和考古遗迹", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_theme_led_query_returns_unesco_clarification_when_api_has_no_cases(self, mock_search) -> None:
        mock_search.return_value = []
        library_path = Path("tests/tmp/articles_theme_with_unesco_fallback.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"世界遗产城市韧性与灾害风险治理框架发布","published_at":"2025-03-10 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/theme-kb-3","local_source_path":"/tmp/a.docx","content_text":"文章系统讨论城市韧性、灾害风险、风险治理与世界遗产城市管理框架。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["城市韧性","灾害风险治理","世界遗产"]}',
                    '{"article_id":"2","title":"历史城区灾害应急保护与恢复机制研究","published_at":"2024-08-01 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/theme-kb-4","local_source_path":"/tmp/b.docx","content_text":"聚焦灾害、应急、恢复和世界遗产地保护机制。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["灾害","应急","恢复","世界遗产地"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例",
            library_path,
            limit=5,
        )

        self.assertIn("当前在UNESCO数据中未检索到与该主题直接匹配的世界遗产地案例。", answer)
        self.assertIn("请问你希望聚焦哪类风险场景？", answer)

    def test_unesco_filter_rejects_weak_climate_or_adaptability_mentions(self) -> None:
        weak_record = {
            "name_zh": "喀尔巴阡山脉及欧洲其它地区的原始山毛榉林",
            "states_names": ["Germany"],
            "date_inscribed": 2007,
            "description_en": "The successful expansion across a whole continent is related to the tree’s adaptability and tolerance of different climatic conditions.",
            "short_description_en": "",
            "justification_en": "",
            "danger": "False",
            "id_no": 1133,
        }

        self.assertEqual(_filter_unesco_world_heritage_sites([weak_record]), [])

    def test_unesco_filter_keeps_strong_threat_plus_response_matches(self) -> None:
        strong_record = {
            "name_zh": "示例遗产地",
            "states_names": ["Exampleland"],
            "date_inscribed": 1999,
            "description_en": "The property faces major climate risk and flood pressure.",
            "short_description_en": "Its conservation management and adaptation strategy address these threats.",
            "justification_en": "",
            "danger": False,
            "id_no": 9999,
        }

        matches = _filter_unesco_world_heritage_sites([strong_record])

        self.assertEqual(len(matches), 1)
        self.assertIn("climate", matches[0]["matched_terms"])
        self.assertIn("risk", matches[0]["matched_terms"])
        self.assertIn("adaptation", matches[0]["matched_terms"])
        self.assertIn("风险信号", matches[0]["relevance_reason"])

    def test_unesco_filter_prefers_query_aligned_case(self) -> None:
        analysis = {
            "primary_theme_terms": ["城市韧性", "灾害治理"],
            "case_carrier_terms": ["世界遗产地", "世界遗产"],
        }
        aligned_record = {
            "name_zh": "主题匹配遗产地",
            "states_names": ["Exampleland"],
            "date_inscribed": 1999,
            "description_en": "The property faces climate risk and flood pressure.",
            "short_description_en": "Its resilience and recovery strategy supports emergency governance.",
            "justification_en": "",
            "danger": False,
            "id_no": 1001,
        }
        weak_record = {
            "name_zh": "弱相关遗产地",
            "states_names": ["Exampleland"],
            "date_inscribed": 1998,
            "description_en": "The property is affected by climate and fire patterns.",
            "short_description_en": "",
            "justification_en": "",
            "danger": False,
            "id_no": 1002,
        }

        matches = _filter_unesco_world_heritage_sites([weak_record, aligned_record], analysis=analysis)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["site_name"], "主题匹配遗产地")
        self.assertIn("命中主题", matches[0]["relevance_reason"])

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_selected_risk_scene_without_unesco_cases_returns_kb_answer_plus_follow_up(self, mock_search) -> None:
        mock_search.return_value = []
        library_path = Path("tests/tmp/articles_scene_follow_up.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"OWHC报告：城市遗产风险管理","published_at":"2023-04-04 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/scene-1","local_source_path":"/tmp/a.docx","content_text":"文章讨论洪水、海平面上升与城市遗产风险管理。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["洪水","风险管理"]}',
                    '{"article_id":"2","title":"气候脆弱性指数在非洲世界遗产的应用研究","published_at":"2024-05-12 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/scene-2","local_source_path":"/tmp/b.docx","content_text":"围绕海平面上升、气候风险和脆弱性评估展开。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["海平面上升","气候风险"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例\n[风险场景A] 洪水 / 海平面上升：洪水 / 海平面上升 / flood / sea level rise / coastal risk / lagoon / water",
            library_path,
            limit=5,
        )

        self.assertIn("OWHC报告：城市遗产风险管理", answer)
        self.assertIn("当前在UNESCO数据中仍未检索到与“洪水 / 海平面上升”直接匹配的稳定世界遗产地案例。", answer)
        self.assertIn("泻湖 / 港口城市与海平面上升", answer)
        self.assertNotIn("请问你希望聚焦哪类风险场景？", answer)

    @patch("guoji_yichan_guancha.query.searchWorldHeritageSites")
    def test_selected_second_layer_scene_without_unesco_cases_returns_narrowed_kb_answer_plus_more_specific_follow_up(
        self,
        mock_search,
    ) -> None:
        mock_search.return_value = []
        library_path = Path("tests/tmp/articles_scene_detail_follow_up.jsonl")
        library_path.parent.mkdir(parents=True, exist_ok=True)
        library_path.write_text(
            "\n".join(
                [
                    '{"article_id":"1","title":"威尼斯泻湖与海平面上升风险研究","published_at":"2024-04-04 20:30","channel":"国际遗产观察","category":"报告资源","source_url":"https://mp.weixin.qq.com/s/detail-1","local_source_path":"/tmp/a.docx","content_text":"文章讨论 lagoon、port city、sea level rise 与 coastal flooding 对遗产城市的影响。","content_html_excerpt":"<p>a</p>","parse_status":"ok","tags_auto":["lagoon","sea level rise"]}',
                    '{"article_id":"2","title":"港口城市潮汐水位与遗产保护治理","published_at":"2024-05-12 20:30","channel":"国际遗产观察","category":"研究","source_url":"https://mp.weixin.qq.com/s/detail-2","local_source_path":"/tmp/b.docx","content_text":"围绕 tidal water、港口城市和长期风险治理展开。","content_html_excerpt":"<p>b</p>","parse_status":"ok","tags_auto":["port city","tidal water"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        answer = answer_question(
            "我需要找城市韧性与灾害治理的信息，包括世界遗产地案例\n"
            "[风险场景A] 洪水 / 海平面上升：洪水 / 海平面上升 / flood / sea level rise / coastal risk / lagoon / water\n"
            "[风险子场景A-1] 泻湖 / 港口城市与海平面上升：lagoon / port city / sea level rise / coastal flooding / tidal water",
            library_path,
            limit=5,
        )

        self.assertIn("威尼斯泻湖与海平面上升风险研究", answer)
        self.assertIn("当前在UNESCO数据中仍未检索到与“泻湖 / 港口城市与海平面上升”直接匹配的稳定世界遗产地案例。", answer)
        self.assertIn("a. 你更想看泻湖城市本体的水位风险，还是港口防洪设施？", answer)
        self.assertNotIn("1. 泻湖 / 港口城市与海平面上升", answer)
        self.assertNotIn("2. 洪水防御、排水系统与城市遗产", answer)

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
