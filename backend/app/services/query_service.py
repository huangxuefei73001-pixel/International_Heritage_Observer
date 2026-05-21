from __future__ import annotations

import logging
import json
from collections import Counter
from pathlib import Path

from guoji_yichan_guancha.query import build_answer_bundle

from app.prompts import load_polish_system_prompt

LOGGER = logging.getLogger(__name__)
_SYSTEM_PROMPT: str | None = None


def _is_library_metadata_question(question: str) -> bool:
    normalized = question.strip().lower()
    if not normalized:
        return False

    mentions_library = any(term in normalized for term in ("kb", "知识库", "资料库", "库里", "库内"))
    asks_metadata = any(
        term in normalized
        for term in (
            "有什么",
            "都有什么",
            "来源",
            "从哪",
            "哪里来",
            "多少",
            "几条",
            "范围",
            "分类",
            "字段",
            "包括",
            "收录",
            "内容",
        )
    )
    return mentions_library and asks_metadata


def _load_library_metadata(library_path: Path) -> dict:
    rows = []
    field_names: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    channels: Counter[str] = Counter()
    parse_statuses: Counter[str] = Counter()
    dates: list[str] = []
    source_url_count = 0
    local_source_path_count = 0

    with library_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(document)
            field_names.update(document.keys())
            categories.update([document.get("category") or "未分类"])
            channels.update([document.get("channel") or ""])
            parse_statuses.update([document.get("parse_status") or ""])
            published_at = document.get("published_at")
            if published_at:
                dates.append(str(published_at)[:10])
            if document.get("source_url"):
                source_url_count += 1
            if document.get("local_source_path"):
                local_source_path_count += 1

    return {
        "count": len(rows),
        "date_min": min(dates) if dates else "",
        "date_max": max(dates) if dates else "",
        "fields": [name for name, _ in field_names.most_common()],
        "categories": categories.most_common(15),
        "channels": channels.most_common(5),
        "parse_statuses": parse_statuses.most_common(5),
        "source_url_count": source_url_count,
        "local_source_path_count": local_source_path_count,
    }


def _format_library_metadata_answer(library_path: Path, metadata: dict) -> str:
    field_labels = {
        "article_id": "文章 ID",
        "title": "文章标题",
        "published_at": "发布时间",
        "channel": "频道",
        "category": "分类",
        "source_url": "原始文章链接",
        "local_source_path": "本地 docx 来源路径",
        "content_text": "正文文本",
        "content_html_excerpt": "HTML 摘录",
        "parse_status": "解析状态",
        "tags_auto": "自动标签",
    }
    fields = [field_labels.get(field, field) for field in metadata["fields"]]
    category_lines = "\n".join(f"- `{name}`：{count}" for name, count in metadata["categories"])
    channel_lines = "、".join(
        f"`{name or '未标注'}` {count} 条" for name, count in metadata["channels"]
    )

    return "\n".join(
        [
            "你问的是知识库本身的范围和来源，不是某个遗产主题的文章检索。",
            "",
            "**KB 里有什么**",
            f"当前知识库共有 `{metadata['count']}` 条文章记录，时间跨度是 `{metadata['date_min']}` 到 `{metadata['date_max']}`。",
            f"主要字段包括：{ '、'.join(f'`{field}`' for field in fields) }。",
            "",
            "主要分类包括：",
            category_lines,
            "",
            "**来源是什么**",
            "这个 KB 来自本地整理的 `国际遗产观察` 文章归档。每条记录保留原始文章链接和本地 docx 来源路径：",
            f"- 有原始文章链接的记录：`{metadata['source_url_count']}` 条",
            f"- 有本地 docx 来源路径的记录：`{metadata['local_source_path_count']}` 条",
            f"- 当前后端读取的库文件：`{library_path}`",
            f"- 频道分布：{channel_lines}",
            "",
            "使用边界：普通遗产问题会按文章内容检索和归纳；像“KB 有什么、来源是什么、收录多少”这类问题，会直接读取知识库元信息来回答。",
        ]
    )


def _library_metadata_answer(question: str, library_path: Path) -> dict | None:
    if not _is_library_metadata_question(question):
        return None
    metadata = _load_library_metadata(library_path)
    return {
        "answer": _format_library_metadata_answer(library_path, metadata),
        "sources": [],
    }


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = load_polish_system_prompt()
    return _SYSTEM_PROMPT


def answer_from_library(
    question: str,
    library_path: Path,
    *,
    strict_source_mode: bool = True,
) -> dict:
    metadata_answer = _library_metadata_answer(question, library_path)
    if metadata_answer is not None:
        return metadata_answer
    return build_answer_bundle(
        question,
        library_path,
        limit=12,
        strict_source_mode=strict_source_mode,
    )


def answer_from_library_with_llm(
    question: str,
    library_path: Path,
    *,
    api_key: str,
    model: str,
    base_url: str = "https://openrouter.ai/api/v1",
    strict_source_mode: bool = True,
) -> dict:
    metadata_answer = _library_metadata_answer(question, library_path)
    if metadata_answer is not None:
        return metadata_answer

    retrieval_result = build_answer_bundle(
        question,
        library_path,
        limit=20,
        strict_source_mode=strict_source_mode,
    )

    if not retrieval_result.get("sources"):
        return retrieval_result

    return _polish_with_llm(
        question=question,
        retrieval_result=retrieval_result,
        library_path=library_path,
        api_key=api_key,
        model=model,
        base_url=base_url,
    )


def _load_source_documents(library_path: Path, sources: list[dict]) -> list[dict]:
    if not sources or not library_path.exists():
        return []
    by_url = {source.get("url"): source for source in sources if source.get("url")}
    by_title = {source.get("title"): source for source in sources if source.get("title")}
    documents = []
    with library_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_url = document.get("source_url")
            title = document.get("title")
            if source_url in by_url or title in by_title:
                documents.append(document)
    return documents


def _extract_document_notes(document: dict) -> list[str]:
    text = " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            document.get("content_text", ""),
        ]
    )
    notes = []
    if any(keyword in text for keyword in ("AR", "增强现实", "导览", "app", "互动地图")):
        notes.append("涉及 AR、移动导览或互动地图等展示增强方式")
    if any(keyword in text for keyword in ("3D", "虚拟游", "虚拟现实", "复原", "数字孪生")):
        notes.append("涉及 3D、虚拟游、复原或数字孪生等可视化展示技术")
    if any(keyword in text for keyword in ("AI", "人工智能", "数字投影", "沉浸", "immersive")):
        notes.append("涉及 AI、沉浸式叙事、数字投影或体验型展示")
    if any(keyword in text for keyword in ("虚拟展", "线上展", "在线展览", "策展", "跨馆")):
        notes.append("涉及虚拟展、跨馆策展或线上展览组织方式")
    if any(keyword in text for keyword in ("平台", "数据库", "资源开放", "视频资源", "数字平台")):
        notes.append("涉及平台、数据库、开放资源或传播基础设施")
    if any(keyword in text for keyword in ("博物馆", "museum", "游客中心", "展示", "传播", "教育")):
        notes.append("与博物馆展示、遗产传播或教育解释直接相关")
    if not notes:
        snippet = document.get("content_text", "").strip().replace("\n", " ")
        if snippet:
            notes.append(f"正文线索：{snippet[:120]}")
    return notes[:3]


def _build_user_message(question: str, retrieval_result: dict, library_path: Path) -> str:
    parts = [
        "请不要复述检索过程，不要说“5条线索”或“从几条线索中提取”。",
        "请直接回答用户问题，并优先按技术类型、实践类型或展示场景重组证据。",
        f"\n## 用户问题\n{question}\n",
    ]
    source_documents = _load_source_documents(library_path, retrieval_result.get("sources", []))
    if source_documents:
        parts.append("## 候选证据")
        for document in source_documents:
            parts.append(
                f"- 《{document['title']}》"
                f"（{document.get('published_at', '')}，{document.get('category', '')}）"
                f"\n  链接：{document.get('source_url', '')}"
            )
            for note in _extract_document_notes(document):
                parts.append(f"  - {note}")
    elif retrieval_result.get("sources"):
        parts.append("## 来源列表")
        for source in retrieval_result["sources"]:
            parts.append(
                f"- [{source['evidence_type']}] 《{source['title']}》"
                f"（{source['published_at']}，{source['category']}）"
                f"  链接：{source['url']}"
            )
    return "\n".join(parts)


def _polish_with_llm(
    question: str,
    retrieval_result: dict,
    library_path: Path,
    api_key: str,
    model: str,
    base_url: str,
) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        LOGGER.warning("openai package not installed, falling back to raw retrieval")
        return retrieval_result

    client = OpenAI(api_key=api_key, base_url=base_url)
    user_message = _build_user_message(question, retrieval_result, library_path)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _get_system_prompt()},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        polished = response.choices[0].message.content
        if polished:
            return {"answer": polished, "sources": retrieval_result["sources"]}
    except Exception:
        LOGGER.exception("LLM polish failed, falling back to raw retrieval")

    return retrieval_result
