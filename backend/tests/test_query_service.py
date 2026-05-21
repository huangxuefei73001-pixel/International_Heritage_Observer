from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.services.query_service import _build_user_message, answer_from_library, answer_from_library_with_llm


def test_answer_from_library_uses_broader_limit(tmp_path):
    library_path = tmp_path / "articles.jsonl"
    library_path.write_text("", encoding="utf-8")

    with patch("app.services.query_service.build_answer_bundle", return_value={"answer": "ok", "sources": []}) as mock_build:
        answer_from_library("test", library_path)

    assert mock_build.call_args.kwargs["limit"] == 12


def test_answer_from_library_returns_library_metadata_for_kb_questions(tmp_path):
    library_path = tmp_path / "articles.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国世界遗产昌德宫5G增强现实游览app",
                "published_at": "2022-06-01 20:30",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/case1",
                "local_source_path": "/tmp/a.docx",
                "content_text": "5G、AR、互动地图与虚拟导游支持遗产地展示。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["AR", "展示"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with patch("app.services.query_service.build_answer_bundle") as mock_build:
        result = answer_from_library("你的KB都有什么？来源是什么？", library_path)

    mock_build.assert_not_called()
    assert "知识库本身的范围和来源" in result["answer"]
    assert "当前知识库共有 `1` 条文章记录" in result["answer"]
    assert "`韩国`：1" in result["answer"]
    assert "原始文章链接" in result["answer"]
    assert result["sources"] == []


def test_answer_from_library_with_llm_uses_broader_limit_and_builds_evidence_message(tmp_path):
    library_path = tmp_path / "articles.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国世界遗产昌德宫5G增强现实游览app",
                "published_at": "2022-06-01 20:30",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/case1",
                "local_source_path": "/tmp/a.docx",
                "content_text": "5G、AR、互动地图与虚拟导游支持遗产地展示。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["AR", "展示"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    retrieval_result = {
        "answer": "基于库内文章归纳：当前问题相关的数字化案例主要可从5条库内线索中提取。",
        "sources": [
            {
                "title": "韩国世界遗产昌德宫5G增强现实游览app",
                "url": "https://mp.weixin.qq.com/s/case1",
                "published_at": "2022-06-01 20:30",
                "category": "韩国",
                "evidence_type": "一般动态",
            }
        ],
    }

    with patch("app.services.query_service.build_answer_bundle", return_value=retrieval_result) as mock_build, patch(
        "app.services.query_service._polish_with_llm",
        return_value=retrieval_result,
    ):
        answer_from_library_with_llm(
            "有什么数字化技术支持遗产地或博物馆展示的实践？",
            library_path,
            api_key="test-key",
            model="openai/gpt-5.4",
        )

    assert mock_build.call_args.kwargs["limit"] == 20

    user_message = _build_user_message(
        "有什么数字化技术支持遗产地或博物馆展示的实践？",
        retrieval_result,
        library_path,
    )
    assert "基于库内文章归纳" not in user_message
    assert "5条库内线索" not in user_message
    assert "候选证据" in user_message
    assert "AR、移动导览或互动地图" in user_message
