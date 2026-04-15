from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.deps import get_db_session, get_settings
from app.main import app
from app.database import Base
from app.models import Conversation, Message, User
from app.services.query_service import answer_from_library
from guoji_yichan_guancha.query import classify_query_type


THEORY_PRACTICE_QUESTION = (
    "近年来国际上对遗产社区参与遗产保护、管理和治理的讨论，"
    "有哪些理论性的成果，对具体实践有哪些国际性的展示、推广、激励性的项目？"
)


def test_classify_query_type_prefers_theory_practice_review():
    assert classify_query_type(THEORY_PRACTICE_QUESTION) == "theory_practice_review"


def test_answer_from_library_uses_theory_practice_review_protocol(tmp_path):
    library_path = tmp_path / "theory_practice_articles.jsonl"
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "ICROM 2021年：新视角下的世界遗产管理实践",
                        "published_at": "2021-08-07 09:30",
                        "channel": "国际遗产观察",
                        "category": "国际治理",
                        "source_url": "https://mp.weixin.qq.com/s/theory-1",
                        "local_source_path": "/tmp/theory-1.docx",
                        "content_text": "people-centred approach、rights-based approach 与 participatory governance 被反复讨论，强调社区参与和利益相关方协商。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["社区参与", "people-centred approach"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "2",
                        "title": "AI解读：UNESCO-WHIPIC价值特征要素与遗产阐释研究报告",
                        "published_at": "2024-02-16 10:00",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/theory-2",
                        "local_source_path": "/tmp/theory-2.docx",
                        "content_text": "heritage interpretation、values attributes 与 stakeholder participation 被放在同一框架下讨论，强调社区共同解释遗产价值。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["价值特征要素", "遗产阐释"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "3",
                        "title": "【研究】世界遗产地管理HIA框架十年应用的批判反思（AI问答）",
                        "published_at": "2024-10-26 12:00",
                        "channel": "国际遗产观察",
                        "category": "研究",
                        "source_url": "https://mp.weixin.qq.com/s/theory-3",
                        "local_source_path": "/tmp/theory-3.docx",
                        "content_text": "critique of expert-led management tools 指出专家主导型管理工具的局限，要求把 stakeholder participation 纳入治理和影响评估。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["HIA", "expert-led"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "4",
                        "title": "ICCROM世界遗产影响评估培训将在杭举行",
                        "published_at": "2024-11-20 09:00",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/practice-1",
                        "local_source_path": "/tmp/practice-1.docx",
                        "content_text": "training、capacity building、workshop 面向实践者推广世界遗产影响评估方法，强调社区参与能力建设。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["培训", "能力建设"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "5",
                        "title": "ICOMOS青年论坛面向社区参与案例征集",
                        "published_at": "2025-05-12 08:30",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/practice-2",
                        "local_source_path": "/tmp/practice-2.docx",
                        "content_text": "forum、call for cases、youth programme 与 competition 结合，展示社区参与遗产治理的国际案例。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["案例征集", "青年论坛"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "6",
                        "title": "【手册】爱尔兰发布世界遗产申报指南",
                        "published_at": "2023-06-18 16:20",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/practice-3",
                        "local_source_path": "/tmp/practice-3.docx",
                        "content_text": "handbook、toolkit 与地方政府指导结合，把社区参与、关键利益相关者协作和申报流程转成可执行工具。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["手册", "toolkit"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "7",
                        "title": "UNESCO社区参与优秀案例奖公布",
                        "published_at": "2025-09-02 14:00",
                        "channel": "国际遗产观察",
                        "category": "一般动态",
                        "source_url": "https://mp.weixin.qq.com/s/practice-4",
                        "local_source_path": "/tmp/practice-4.docx",
                        "content_text": "award、prize 与 international recognition 被用来激励社区参与、展示推广优秀项目。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["award", "prize"],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = answer_from_library(THEORY_PRACTICE_QUESTION, library_path)
    answer = result["answer"]

    assert "问题理解：" in answer
    assert "库内结论：" in answer
    assert "理论性的成果：" in answer
    assert "对应的国际性实践机制/项目：" in answer
    assert "可直接用于写作的归纳：" in answer
    assert "证据文章：" in answer
    assert "证据边界：" in answer

    assert "被关注的要点：" not in answer
    assert "难点：" not in answer
    assert "探索实践：" not in answer
    assert "如果压缩成一句判断：" not in answer

    forbidden_phrases = [
        "可从几条线索中提取",
        "当前材料更适合提炼实践路径",
        "更关注",
        "说明这一议题已进入制度调整层面",
        "相关的相关案例",
    ]
    assert not any(phrase in answer for phrase in forbidden_phrases)

    theory_section = _extract_section(answer, "理论性的成果：", "对应的国际性实践机制/项目：")
    practice_section = _extract_section(answer, "对应的国际性实践机制/项目：", "可直接用于写作的归纳：")
    assert theory_section.count("- ") >= 3
    assert practice_section.count("- ") >= 3

    assert "[ICROM 2021年：新视角下的世界遗产管理实践](https://mp.weixin.qq.com/s/theory-1)" in answer
    assert "[AI解读：UNESCO-WHIPIC价值特征要素与遗产阐释研究报告](https://mp.weixin.qq.com/s/theory-2)" in answer
    assert "[【研究】世界遗产地管理HIA框架十年应用的批判反思（AI问答）](https://mp.weixin.qq.com/s/theory-3)" in answer
    assert "[ICCROM世界遗产影响评估培训将在杭举行](https://mp.weixin.qq.com/s/practice-1)" in answer
    assert "[ICOMOS青年论坛面向社区参与案例征集](https://mp.weixin.qq.com/s/practice-2)" in answer
    assert "[【手册】爱尔兰发布世界遗产申报指南](https://mp.weixin.qq.com/s/practice-3)" in answer

    source_titles = {item["title"] for item in result["sources"]}
    assert "ICROM 2021年：新视角下的世界遗产管理实践" in source_titles
    assert "ICCROM世界遗产影响评估培训将在杭举行" in source_titles


def test_theory_review_does_not_use_forum_or_training_fallback_when_only_two_strong_docs(tmp_path):
    library_path = tmp_path / "theory_review_only_two_strong_docs.jsonl"
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "ICCROM年报：以人为中心方法与遗产治理框架更新",
                        "published_at": "2021-08-07 09:30",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/theory-a",
                        "local_source_path": "/tmp/theory-a.docx",
                        "content_text": "people-centred approach、rights-based approach 与 participatory governance 被作为遗产治理框架更新的核心概念。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["people-centred approach"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "2",
                        "title": "AI解读：UNESCO-WHIPIC价值特征要素与遗产阐释研究报告",
                        "published_at": "2024-02-16 10:00",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/theory-b",
                        "local_source_path": "/tmp/theory-b.docx",
                        "content_text": "heritage interpretation、values attributes 与 stakeholder participation 被纳入同一分析框架。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["价值特征要素", "遗产阐释"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "3",
                        "title": "遗产社区参与国际论坛在意大利召开",
                        "published_at": "2025-05-11 08:30",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/forum-only",
                        "local_source_path": "/tmp/forum-only.docx",
                        "content_text": "forum、conference、community participation，介绍论坛议程和嘉宾名单。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["论坛"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "4",
                        "title": "ICCROM社区参与培训班开放报名",
                        "published_at": "2025-06-03 09:00",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/training-only",
                        "local_source_path": "/tmp/training-only.docx",
                        "content_text": "training、capacity building、workshop，介绍培训安排与报名方式。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["培训"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "5",
                        "title": "【手册】爱尔兰发布世界遗产申报指南",
                        "published_at": "2023-06-18 16:20",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/handbook-a",
                        "local_source_path": "/tmp/handbook-a.docx",
                        "content_text": "handbook、toolkit 与地方政府指导结合，把社区参与和协作流程转成可执行工具。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["手册", "toolkit"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "6",
                        "title": "UNESCO社区参与优秀案例奖公布",
                        "published_at": "2025-09-02 14:00",
                        "channel": "国际遗产观察",
                        "category": "一般动态",
                        "source_url": "https://mp.weixin.qq.com/s/award-a",
                        "local_source_path": "/tmp/award-a.docx",
                        "content_text": "award、prize 与 international recognition 被用来激励社区参与项目。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["award", "prize"],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = answer_from_library(THEORY_PRACTICE_QUESTION, library_path)
    answer = result["answer"]
    theory_section = _extract_section(answer, "理论性的成果：", "对应的国际性实践机制/项目：")

    assert theory_section.count("- ") == 2
    assert "ICCROM年报：以人为中心方法与遗产治理框架更新" in theory_section
    assert "AI解读：UNESCO-WHIPIC价值特征要素与遗产阐释研究报告" in theory_section
    assert "遗产社区参与国际论坛在意大利召开" not in theory_section
    assert "ICCROM社区参与培训班开放报名" not in theory_section
    assert "库内现有材料对理论层面的覆盖较弱，目前只能稳定支撑2条理论归纳。" in answer
    assert "该文直接把社区参与与遗产保护、管理和治理框架放在同一讨论中" not in answer
    assert "理论部分可概括为“治理框架重组—价值阐释重写—工具反思”三层结构。" not in answer


def test_theory_practice_review_prefers_real_handbook_and_limits_homogeneous_training_sources(tmp_path):
    library_path = tmp_path / "theory_practice_diversified_sources.jsonl"
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "ICCROM年报：以人为中心方法与遗产治理框架更新",
                        "published_at": "2021-08-07 09:30",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/theory-c",
                        "local_source_path": "/tmp/theory-c.docx",
                        "content_text": "people-centred approach、rights-based approach 与 participatory governance 被作为遗产治理框架更新的核心概念。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["people-centred approach"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "2",
                        "title": "AI解读：UNESCO-WHIPIC价值特征要素与遗产阐释研究报告",
                        "published_at": "2024-02-16 10:00",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/theory-d",
                        "local_source_path": "/tmp/theory-d.docx",
                        "content_text": "heritage interpretation、values attributes 与 stakeholder participation 被纳入同一分析框架。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["价值特征要素", "遗产阐释"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "3",
                        "title": "【研究】世界遗产地管理HIA框架十年应用的批判反思（AI问答）",
                        "published_at": "2024-10-26 12:00",
                        "channel": "国际遗产观察",
                        "category": "研究",
                        "source_url": "https://mp.weixin.qq.com/s/theory-e",
                        "local_source_path": "/tmp/theory-e.docx",
                        "content_text": "critique of expert-led management tools 指出专家主导型管理工具的局限，要求把 stakeholder participation 纳入治理和影响评估。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["expert-led"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "4",
                        "title": "ICCROM社区参与培训班开放报名",
                        "published_at": "2025-07-03 09:00",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/iccrom-training-1",
                        "local_source_path": "/tmp/iccrom-training-1.docx",
                        "content_text": "training、capacity building、workshop，并附项目操作指南与案例包下载说明。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["培训"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "5",
                        "title": "ICCROM社区参与培训营将在罗马举行",
                        "published_at": "2025-07-04 09:00",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/iccrom-training-2",
                        "local_source_path": "/tmp/iccrom-training-2.docx",
                        "content_text": "training、capacity building、workshop，介绍课程安排。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["培训"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "6",
                        "title": "ICCROM社区参与培训项目开放申请",
                        "published_at": "2025-07-05 09:00",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/iccrom-training-3",
                        "local_source_path": "/tmp/iccrom-training-3.docx",
                        "content_text": "training、capacity building 与 workshop 面向不同遗产地项目团队。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["培训"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "7",
                        "title": "【手册】爱尔兰发布世界遗产申报指南",
                        "published_at": "2023-06-18 16:20",
                        "channel": "国际遗产观察",
                        "category": "报告资源",
                        "source_url": "https://mp.weixin.qq.com/s/real-handbook",
                        "local_source_path": "/tmp/real-handbook.docx",
                        "content_text": "handbook、toolkit 与地方政府指导结合，把社区参与和协作流程转成可执行工具。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["手册", "toolkit"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "8",
                        "title": "ICOMOS青年论坛面向社区参与案例征集",
                        "published_at": "2025-05-12 08:30",
                        "channel": "国际遗产观察",
                        "category": "会议新闻",
                        "source_url": "https://mp.weixin.qq.com/s/case-collection",
                        "local_source_path": "/tmp/case-collection.docx",
                        "content_text": "forum、call for cases、case collection，征集社区参与案例。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["案例征集"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "article_id": "9",
                        "title": "UNESCO社区参与优秀案例奖公布",
                        "published_at": "2025-09-02 14:00",
                        "channel": "国际遗产观察",
                        "category": "一般动态",
                        "source_url": "https://mp.weixin.qq.com/s/award-b",
                        "local_source_path": "/tmp/award-b.docx",
                        "content_text": "award、prize 与 international recognition 被用来激励社区参与项目。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["award", "prize"],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = answer_from_library(THEORY_PRACTICE_QUESTION, library_path)
    answer = result["answer"]
    practice_section = _extract_section(answer, "对应的国际性实践机制/项目：", "可直接用于写作的归纳：")

    assert "【手册】爱尔兰发布世界遗产申报指南" in practice_section
    assert "ICCROM社区参与培训班开放报名" in practice_section
    assert "ICCROM社区参与培训营将在罗马举行" not in practice_section
    assert "ICCROM社区参与培训项目开放申请" not in practice_section

    source_titles = [item["title"] for item in result["sources"]]
    assert "【手册】爱尔兰发布世界遗产申报指南" in source_titles
    assert sum(title.startswith("ICCROM社区参与培训") for title in source_titles) <= 1


def _extract_section(answer: str, start_marker: str, end_marker: str) -> str:
    start = answer.index(start_marker) + len(start_marker)
    end = answer.index(end_marker, start)
    return answer[start:end]


def test_answer_from_library_returns_structured_blocks():
    library_path = Path("tests/tmp/chat_articles.jsonl")
    library_path.parent.mkdir(parents=True, exist_ok=True)
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "韩国召开第48届世界遗产大会联席工作会",
                        "published_at": "2026-03-20 11:25",
                        "channel": "国际遗产观察",
                        "category": "韩国",
                        "source_url": "https://mp.weixin.qq.com/s/example",
                        "local_source_path": "/tmp/a.docx",
                        "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["韩国", "世界遗产大会"],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = answer_from_library("最近韩国有什么世界遗产动态？", library_path)

    assert "answer" in result
    assert "sources" in result
    assert "问题理解：" in result["answer"]
    assert "库内结论：" in result["answer"]
    assert "被关注的要点：" in result["answer"]
    assert "探索实践：" in result["answer"]
    assert "如果压缩成一句判断：" in result["answer"]
    assert "证据文章：" in result["answer"]
    assert "证据边界：" in result["answer"]
    assert "[韩国召开第48届世界遗产大会联席工作会](https://mp.weixin.qq.com/s/example)" in result["answer"]
    assert "| https://mp.weixin.qq.com/s/example" not in result["answer"]
    assert result["sources"][0]["title"] == "韩国召开第48届世界遗产大会联席工作会"
    assert result["sources"][0]["url"] == "https://mp.weixin.qq.com/s/example"
    assert result["sources"][0]["published_at"] == "2026-03-20 11:25"
    assert result["sources"][0]["category"] == "韩国"
    assert result["sources"][0]["evidence_type"] == "一般动态"


def test_chat_ask_endpoint_returns_structured_answer():
    library_path = Path("tests/tmp/chat_endpoint_articles.jsonl")
    library_path.parent.mkdir(parents=True, exist_ok=True)
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "韩国召开第48届世界遗产大会联席工作会",
                        "published_at": "2026-03-20 11:25",
                        "channel": "国际遗产观察",
                        "category": "韩国",
                        "source_url": "https://mp.weixin.qq.com/s/example",
                        "local_source_path": "/tmp/a.docx",
                        "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["韩国", "世界遗产大会"],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client, engine, _ = _build_chat_test_client(library_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "sources" in body
    assert body["sources"][0]["url"] == "https://mp.weixin.qq.com/s/example"


def test_chat_ask_endpoint_returns_controlled_error_when_library_is_missing():
    missing_path = Path(tempfile.gettempdir()) / "does-not-exist-chat-library.jsonl"
    if missing_path.exists():
        missing_path.unlink()

    client, engine, _ = _build_chat_test_client(missing_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Library not available"


def _build_chat_test_client(library_path: Path):
    database_url = f"sqlite:///{library_path.parent / 'chat.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_settings():
        return Settings(
            database_url=database_url,
            session_secret="secret",
            openrouter_api_key="test-key",
            openrouter_model="openai/gpt-4.1-mini",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            smtp_sender="bot@example.com",
            library_path=str(library_path),
        )

    def override_get_db_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app, raise_server_exceptions=False)
    return client, engine, session_factory


def test_chat_ask_creates_conversation_and_messages(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] is not None
    assert body["messages_saved"] == 2

    with session_factory() as db:
        conversation = db.execute(select(Conversation)).scalar_one()
        messages = db.execute(select(Message).order_by(Message.id)).scalars().all()
        user = db.execute(select(User).where(User.email == "user@example.com")).scalar_one()

    assert conversation.user_id == user.id
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].sources_json is not None


def test_chat_ask_reuses_existing_conversation(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            user = User(email="user@example.com", role="user")
            db.add(user)
            db.flush()
            conversation = Conversation(user_id=user.id, title="Existing")
            db.add(conversation)
            db.flush()
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == conversation.id)
                .values(updated_at=datetime(2024, 1, 1, 0, 0, 0))
            )
            conversation_id = conversation.id
            db.commit()

        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": conversation_id},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id
    assert response.json()["messages_saved"] == 2

    with session_factory() as db:
        conversation = db.execute(select(Conversation).where(Conversation.id == conversation_id)).scalar_one()
        messages = db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).scalars().all()

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert conversation.updated_at > datetime(2024, 1, 1, 0, 0, 0)


def test_chat_ask_rejects_other_users_conversation(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            owner = User(email="owner@example.com", role="user")
            intruder = User(email="intruder@example.com", role="user")
            db.add_all([owner, intruder])
            db.flush()
            conversation = Conversation(user_id=owner.id, title="Owner")
            db.add(conversation)
            db.flush()
            conversation_id = conversation.id
            db.commit()

        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "intruder@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": conversation_id},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Conversation not found"


def test_chat_ask_keeps_user_message_when_answer_generation_fails(tmp_path, monkeypatch):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)
    monkeypatch.setattr(
        "app.routers.chat.answer_from_library",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 502
    assert response.json()["detail"]["conversation_id"] is not None

    with session_factory() as db:
        conversations = db.execute(select(Conversation)).scalars().all()
        messages = db.execute(select(Message).order_by(Message.id)).scalars().all()

    assert len(conversations) == 1
    assert len(messages) == 1
    assert messages[0].role == "user"


def test_chat_ask_returns_controlled_error_when_user_header_missing(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, _ = _build_chat_test_client(library_path)

    try:
        response = client.post("/chat/ask", json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-Debug-User"


def test_chat_conversations_lists_only_current_user_threads(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text("", encoding="utf-8")
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            owner = User(email="owner@example.com", role="user")
            stranger = User(email="stranger@example.com", role="user")
            db.add_all([owner, stranger])
            db.flush()

            owner_old = Conversation(user_id=owner.id, title="旧问题")
            owner_new = Conversation(user_id=owner.id, title="新问题")
            stranger_thread = Conversation(user_id=stranger.id, title="别人的问题")
            db.add_all([owner_old, owner_new, stranger_thread])
            db.flush()

            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == owner_old.id)
                .values(updated_at=datetime(2024, 1, 1, 0, 0, 0))
            )
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == owner_new.id)
                .values(updated_at=datetime(2024, 1, 2, 0, 0, 0))
            )
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == stranger_thread.id)
                .values(updated_at=datetime(2024, 1, 3, 0, 0, 0))
            )
            db.commit()

        response = client.get(
            "/chat/conversations",
            headers={"X-Debug-User": "owner@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body] == ["新问题", "旧问题"]
    assert all("user_email" not in item for item in body)


def test_chat_conversation_detail_returns_only_owned_messages(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text("", encoding="utf-8")
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            owner = User(email="owner@example.com", role="user")
            stranger = User(email="stranger@example.com", role="user")
            db.add_all([owner, stranger])
            db.flush()

            conversation = Conversation(user_id=owner.id, title="韩国动态")
            db.add(conversation)
            db.flush()
            db.add_all(
                [
                    Message(conversation_id=conversation.id, role="user", content="韩国有什么动态？"),
                    Message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content="这里是回答",
                        sources_json=json.dumps(
                            [
                                {
                                    "title": "韩国召开会议",
                                    "url": "https://example.com/a",
                                    "published_at": "2026-03-20 11:25",
                                    "category": "韩国",
                                    "evidence_type": "一般动态",
                                }
                            ],
                            ensure_ascii=False,
                        ),
                    ),
                ]
            )
            db.commit()
            conversation_id = conversation.id

        owner_response = client.get(
            f"/chat/conversations/{conversation_id}",
            headers={"X-Debug-User": "owner@example.com"},
        )
        stranger_response = client.get(
            f"/chat/conversations/{conversation_id}",
            headers={"X-Debug-User": "stranger@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert owner_response.status_code == 200
    detail = owner_response.json()
    assert detail["title"] == "韩国动态"
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["sources"][0]["title"] == "韩国召开会议"

    assert stranger_response.status_code == 404
    assert stranger_response.json()["detail"] == "Conversation not found"
