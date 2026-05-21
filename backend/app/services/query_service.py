from __future__ import annotations

import logging
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from guoji_yichan_guancha.query import build_answer_bundle, infer_evidence_type

from app.prompts import load_polish_system_prompt

LOGGER = logging.getLogger(__name__)
_SYSTEM_PROMPT: str | None = None

RECENT_HOTSPOT_THEMES = (
    {
        "label": "世界遗产治理与管理体系更新",
        "keywords": (
            "世界遗产",
            "管理",
            "治理",
            "申报",
            "预评估",
            "影响评估",
            "HIA",
            "操作指南",
            "委员会",
            "OUV",
            "名录",
        ),
        "description": "世界遗产大会、申报评估、管理规划、保护状况和影响评估持续出现，是最近一年最稳定的主线。",
        "preferred_titles": (
            "UNESCO同韩国签署第48届世界遗产大会协议",
            "ICOMOS世界遗产评估部招募助理",
            "第48届世界遗产大会第二次联合现场检查完成",
        ),
    },
    {
        "label": "城市遗产、再生与可持续发展",
        "keywords": ("城市", "再生", "更新", "住房", "景观", "规划", "可持续", "再利用", "发展", "历史城区"),
        "description": "遗产越来越被放进城市更新、历史城区再生、地方发展和空间规划里讨论。",
        "preferred_titles": (
            "CHiFA-OWHC 城市遗产再生加速器项目报告",
            "ICCROM发布遗产与景观专业培训手册",
        ),
    },
    {
        "label": "旅游影响与参与式治理",
        "keywords": ("旅游", "游客", "参与式", "承载力", "体验", "社区", "非遗", "地方生活"),
        "description": "旅游议题从传播和收益，转向游客体验、社区参与、非遗延续和地方生活之间的平衡。",
        "preferred_titles": (
            "城市环境中世界遗产和非遗应对旅游影响的参与式路径研究",
            "撒马尔罕世界遗产阐释效果研究：遗产机构的叙事与游客体验",
        ),
    },
    {
        "label": "社区参与、以人为中心与包容性遗产",
        "keywords": ("社区", "以人为中心", "包容", "参与", "原住民", "地方", "青年", "多元", "口述史", "活态"),
        "description": "社区参与继续升温，并进一步连接包容性、地方知识、青年参与和以人为中心的管理。",
        "preferred_titles": (
            "特刊：走向以人为中心的考古遗产管理路径",
            "苏格兰考古学会7月线上讨论包容性社区参与",
            "HMO文化遗产社区参与夏令营6月在希腊举办",
        ),
    },
    {
        "label": "数字化、AI、BIM与遗产信息系统",
        "keywords": ("数字", "AI", "人工智能", "BIM", "3D", "三维", "虚拟", "平台", "数据", "信息系统", "数字叙事"),
        "description": "数字化从展示工具扩展到记录、管理、监测、BIM、数字叙事和遗产信息系统。",
        "preferred_titles": (
            "奈文研石垣BIM遗产信息系统研究",
            "第四届欧洲数字叙事节即将启动",
            "【书讯】从笔到比特：古罗马广场的研究与世界遗产的数字化未来",
        ),
    },
    {
        "label": "气候变化、能源转型与灾害风险",
        "keywords": ("气候", "灾害", "风险", "韧性", "能源", "能效", "热泵", "太阳能", "火灾", "洪水", "易损性"),
        "description": "气候适应、灾害风险、建筑能效和能源转型正在进入技术指南与工程决策。",
        "preferred_titles": (
            "ICOMOS欧洲建筑能效令与文化遗产报告",
            "英格兰历史建筑水源热泵可行性研究",
            "庞贝考古遗存墙体平面外易损性评估方法研究",
        ),
    },
    {
        "label": "博物馆、创意政策与遗产传播",
        "keywords": ("博物馆", "创意", "传播", "阐释", "展示", "教育", "展览", "叙事", "导览", "公众"),
        "description": "博物馆、创意政策、阐释展示和数字叙事仍是遗产传播端的活跃议题。",
        "preferred_titles": (
            "UNESCO发布第四版重塑创意政策报告",
            "英国UNESCO全委会发布遗产地对策案例平台",
            "第四届欧洲数字叙事节即将启动",
        ),
    },
)


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


def _parse_published_date(document: dict) -> datetime | None:
    published_at = document.get("published_at")
    if not published_at:
        return None
    try:
        return datetime.fromisoformat(str(published_at).replace(" ", "T"))
    except ValueError:
        try:
            return datetime.strptime(str(published_at)[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _is_recent_hotspot_question(question: str) -> bool:
    normalized = question.strip()
    if not normalized:
        return False
    has_scope = any(term in normalized for term in ("最近一年", "近一年", "这一年", "过去一年", "2025", "2026"))
    has_domain = any(term in normalized for term in ("国际遗产界", "遗产界", "国际遗产", "世界遗产"))
    asks_hotspot = any(term in normalized for term in ("热点", "关注", "趋势", "动向", "议题"))
    return has_scope and has_domain and asks_hotspot


def _load_documents(library_path: Path) -> list[dict]:
    documents = []
    with library_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                documents.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return documents


def _document_text(document: dict) -> str:
    return " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            document.get("content_text", ""),
        ]
    )


def _theme_match_count(document: dict, keywords: tuple[str, ...]) -> int:
    text = _document_text(document).lower()
    title = document.get("title", "").lower()
    count = 0
    for keyword in keywords:
        normalized = keyword.lower()
        if normalized in title:
            count += 3
        elif normalized in text:
            count += 1
    return count


def _select_theme_sources(
    documents: list[dict],
    keywords: tuple[str, ...],
    preferred_titles: tuple[str, ...] = (),
    limit: int = 2,
) -> list[dict]:
    selected = []
    seen = set()
    by_title = {document.get("title", ""): document for document in documents}
    for title in preferred_titles:
        document = by_title.get(title)
        if not document:
            continue
        key = document.get("source_url") or document.get("title")
        if key in seen:
            continue
        selected.append(document)
        seen.add(key)
        if len(selected) >= limit:
            return selected

    scored = []
    for document in documents:
        score = _theme_match_count(document, keywords)
        if score <= 0:
            continue
        published_at = document.get("published_at", "")
        scored.append((score, published_at, document))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    for _score, _published_at, document in scored:
        key = document.get("source_url") or document.get("title")
        if key in seen:
            continue
        selected.append(document)
        seen.add(key)
        if len(selected) >= limit:
            break
    return selected


def _source_from_document(document: dict) -> dict:
    return {
        "title": document.get("title", ""),
        "url": document.get("source_url", ""),
        "published_at": document.get("published_at", ""),
        "category": document.get("category", ""),
        "evidence_type": infer_evidence_type(document),
    }


def _format_recent_hotspot_answer(
    *,
    start_date: datetime,
    end_date: datetime,
    documents: list[dict],
    theme_rows: list[dict],
    sources: list[dict],
) -> str:
    lines = [
        f"问题理解：你问的是最近一年国际遗产界的整体关注热点。我按库内最新时间往前一年统计，即 `{start_date.date()}` 到 `{end_date.date()}`；这个区间库内共有 `{len(documents)}` 条文章。",
        "",
        "库内结论：最近一年国际遗产界的热点，不是单一事件，而是几组持续升温的议题：",
        "",
    ]
    for index, row in enumerate(theme_rows, start=1):
        source_titles = "、".join(
            f"[{source['title']}]({source['url']})" for source in row["sources"] if source.get("url")
        )
        evidence_tail = f"代表文章：{source_titles}" if source_titles else "代表文章：库内暂无足够清晰的单篇代表材料。"
        lines.append(
            f"{index}. `{row['label']}`  \n"
            f"{row['description']}库内相关命中约 `{row['count']}` 条。{evidence_tail}"
        )
    lines.extend(
        [
            "",
            "可直接用于写作的归纳：最近一年国际遗产界的关注重心，正在从单纯的遗产本体保护，转向 `治理体系更新、城市与旅游压力、社区和包容性、数字化管理、气候风险与能源转型` 这些更综合的议题。",
            "",
            f"证据边界：这是基于本地 `国际遗产观察` 库内最近一年文章归纳；库内最新记录到 `{end_date.date()}`。来源列表保留为本次热点判断中最具代表性的文章。",
        ]
    )
    return "\n".join(lines)


def _recent_hotspot_answer(question: str, library_path: Path) -> dict | None:
    if not _is_recent_hotspot_question(question):
        return None

    all_documents = _load_documents(library_path)
    dated = [(date_value, document) for document in all_documents if (date_value := _parse_published_date(document))]
    if not dated:
        return None

    end_date = max(date_value for date_value, _document in dated)
    start_date = end_date - timedelta(days=364)
    recent_documents = [document for date_value, document in dated if start_date <= date_value <= end_date]
    if not recent_documents:
        return None

    theme_rows = []
    source_documents = []
    for theme in RECENT_HOTSPOT_THEMES:
        matching_documents = [
            document
            for document in recent_documents
            if _theme_match_count(document, theme["keywords"]) > 0
        ]
        if not matching_documents:
            continue
        selected_documents = _select_theme_sources(
            matching_documents,
            theme["keywords"],
            theme.get("preferred_titles", ()),
        )
        source_documents.extend(selected_documents)
        theme_rows.append(
            {
                "label": theme["label"],
                "description": theme["description"],
                "count": len(matching_documents),
                "sources": [_source_from_document(document) for document in selected_documents],
            }
        )

    # Keep the curated order, but drop very thin categories if the library does not support them.
    theme_rows = [row for row in theme_rows if row["count"] >= 2][:7]
    sources = []
    seen = set()
    for document in source_documents:
        source = _source_from_document(document)
        key = source["url"] or source["title"]
        if key in seen:
            continue
        sources.append(source)
        seen.add(key)

    return {
        "answer": _format_recent_hotspot_answer(
            start_date=start_date,
            end_date=end_date,
            documents=recent_documents,
            theme_rows=theme_rows,
            sources=sources,
        ),
        "sources": sources,
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
    hotspot_answer = _recent_hotspot_answer(question, library_path)
    if hotspot_answer is not None:
        return hotspot_answer
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
    hotspot_answer = _recent_hotspot_answer(question, library_path)
    if hotspot_answer is not None:
        return hotspot_answer

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
