from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path


DOMAIN_PHRASES = [
    "世界遗产大会",
    "世界遗产",
    "申遗",
    "遗产阐释",
    "阐释展示",
    "影响评估",
    "管理规划",
    "过度旅游",
    "气候变化",
    "数字化",
    "数字记录",
    "数字存档",
    "数字平台",
    "数据库",
    "数字孪生",
    "三维",
    "3D",
    "人工智能",
    "AI",
]
QUESTION_STOP_WORDS = {
    "什么",
    "最近",
    "近年",
    "哪些",
    "几个",
    "关于",
    "案例",
    "动态",
    "问题",
    "请问",
    "帮我",
    "整理",
    "一下",
    "有关",
}
REPORT_KEYWORDS = ("报告", "研究", "手册", "指南", "年报", "白皮书", "蓝皮书", "论文", "评估")
BOOK_KEYWORDS = ("新书", "书讯", "丛书", "专著", "出版", "杂志", "期刊", "论文集")
MEETING_KEYWORDS = ("会议", "论坛", "研讨会", "讲座", "工作坊", "年会", "夏令营", "培训", "招募", "征集", "活动")
POLICY_KEYWORDS = ("预算", "规划", "基本法", "公布", "通过", "发布", "启动", "开放", "推出", "措施", "改革")
DIGITAL_HIGH_SIGNAL = ("数字化", "数字记录", "数字存档", "数字平台", "数据库", "数字孪生", "三维", "3D")
DIGITAL_BROAD_SIGNAL = (
    "数字遗产",
    "数字保护",
    "数字转型",
    "数字修复",
    "智能化修复",
    "建模",
    "虚拟现实",
    "增强现实",
    "AR",
    "VR",
    "区块链",
    "Web3",
    "NFT",
)
HERITAGE_BROAD_SIGNAL = (
    "文化遗产",
    "遗产保护",
    "遗产管理",
    "遗产展示",
    "遗产阐释",
    "世界遗产",
)


def infer_evidence_type(document: dict) -> str:
    title_haystack = " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
        ]
    )
    content_text = document.get("content_text", "")
    if any(keyword in title_haystack for keyword in REPORT_KEYWORDS) or "研究报告" in content_text:
        return "报告资源"
    if any(keyword in title_haystack for keyword in BOOK_KEYWORDS):
        return "书刊资讯"
    if any(keyword in title_haystack for keyword in MEETING_KEYWORDS):
        return "会议新闻"
    if any(keyword in title_haystack for keyword in POLICY_KEYWORDS):
        return "政策动态"
    return "一般动态"


def _has_digital_signal(document: dict) -> bool:
    haystack = " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            document.get("content_text", ""),
        ]
    )
    return any(signal in haystack for signal in DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL)


def _has_broader_heritage_digital_signal(document: dict) -> bool:
    haystack = " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            document.get("content_text", ""),
        ]
    )
    has_digital = any(signal in haystack for signal in DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL)
    has_heritage = any(signal in haystack for signal in HERITAGE_BROAD_SIGNAL)
    return has_digital and has_heritage


def _detect_task_type(question: str) -> str:
    if any(token in question for token in ("是什么", "怎么界定", "定义", "概念", "何为", "什么意思")):
        return "concept"
    if any(token in question for token in ("趋势", "动向", "脉络", "进展", "发展", "综述", "研究")):
        return "trend"
    if any(token in question for token in ("案例", "例子", "几个", "哪些", "实践", "经验")):
        return "case"
    return "dynamic"


def _tokenize(question: str) -> list[str]:
    tokens = [token for token in DOMAIN_PHRASES if token in question]
    for chunk in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", question):
        if len(chunk) >= 2:
            tokens.append(chunk)
    return list(dict.fromkeys(tokens))


def _extract_thematic_terms(question: str, category_hits: list[str], years: list[str]) -> list[str]:
    terms = [phrase for phrase in DOMAIN_PHRASES if phrase in question]
    normalized = question
    for year in years:
        normalized = normalized.replace(f"{year}年", " ")
    normalized = re.sub(
        r"(最近|近年|关于|几个|哪些|什么|有什么|请问|帮我|整理|一下|案例|动态|的)",
        " ",
        normalized,
    )
    chunks = [chunk for chunk in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", normalized) if len(chunk) >= 2]
    for chunk in chunks:
        if chunk not in QUESTION_STOP_WORDS and chunk not in category_hits:
            terms.append(chunk)
        for size in range(2, min(7, len(chunk) + 1)):
            for index in range(0, len(chunk) - size + 1):
                piece = chunk[index : index + size]
                if (
                    len(piece) >= 2
                    and re.search(r"[\u4e00-\u9fffA-Za-z]", piece)
                    and piece not in QUESTION_STOP_WORDS
                    and piece not in category_hits
                    and not any(year in piece for year in years)
                ):
                    terms.append(piece)
    return list(dict.fromkeys(terms))


def _parse_relative_year_window(question: str, reference_date: date) -> tuple[str | None, str | None]:
    if "近三年" in question:
        start_year = reference_date.year - 3
        return f"{start_year}-01-01", f"{reference_date.year}-12-31"
    if "近两年" in question:
        start_year = reference_date.year - 2
        return f"{start_year}-01-01", f"{reference_date.year}-12-31"
    if "近一年" in question:
        return f"{reference_date.year - 1}-01-01", f"{reference_date.year}-12-31"
    return None, None


def _parse_published_at(value: str) -> date | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _analyze_question(question: str, documents: list[dict], reference_date: date) -> dict:
    categories = sorted({document.get("category", "") for document in documents if document.get("category")})
    years = re.findall(r"(20\d{2})年", question)
    category_hits = [category for category in categories if category and category in question]
    domain_hits = [phrase for phrase in DOMAIN_PHRASES if phrase in question]
    phrases = _tokenize(question)
    thematic_terms = _extract_thematic_terms(question, category_hits, years)
    relative_start, relative_end = _parse_relative_year_window(question, reference_date)
    return {
        "years": years,
        "category_hits": category_hits,
        "domain_hits": domain_hits,
        "phrases": phrases,
        "thematic_terms": thematic_terms,
        "task_type": _detect_task_type(question),
        "wants_recent": "最近" in question or "动态" in question,
        "relative_start": relative_start,
        "relative_end": relative_end,
        "digital_focus": any(signal in question for signal in DIGITAL_HIGH_SIGNAL),
    }


def _primary_focus(question: str, analysis: dict) -> str:
    if analysis["digital_focus"] and analysis["task_type"] == "trend":
        return "遗产数字化发展"
    if analysis["task_type"] == "concept":
        if analysis["domain_hits"]:
            return analysis["domain_hits"][0]
        if analysis["thematic_terms"]:
            return analysis["thematic_terms"][0]
        return "相关概念"
    if analysis["task_type"] == "trend":
        if analysis["domain_hits"]:
            return f"{analysis['domain_hits'][0]}趋势"
        return "相关趋势"
    if analysis["task_type"] == "case":
        if analysis["domain_hits"]:
            return f"{analysis['domain_hits'][0]}案例"
        return "相关案例"
    if "动态" in question or analysis["wants_recent"]:
        if "世界遗产" in question:
            return "世界遗产动态"
        return "相关动态"
    if analysis["phrases"]:
        return analysis["phrases"][0]
    return "相关议题"


def _build_conclusion(question: str, analysis: dict, matches: list[dict]) -> str:
    prefix = ""
    if analysis["years"]:
        prefix += f"{analysis['years'][0]}年"
    if analysis["category_hits"]:
        prefix += analysis["category_hits"][0]
    focus = _primary_focus(question, analysis)
    if not prefix:
        prefix = "当前问题"
    if analysis["task_type"] == "concept":
        return f"{prefix}涉及的{focus}定义主要可从{len(matches)}条库内线索中把握。"
    if analysis["task_type"] == "trend":
        return f"{prefix}涉及的{focus}主要可从{len(matches)}条库内线索中归纳。"
    if analysis["task_type"] == "case":
        return f"{prefix}相关的{focus}主要可从{len(matches)}条库内线索中提取。"
    return f"{prefix}的{focus}主要集中在{len(matches)}条库内线索。"


def _build_takeaways(conclusion: str, matches: list[dict]) -> list[str]:
    takeaways = [conclusion]
    for document in matches[:3]:
        takeaways.append(
            f"{document['published_at']}的《{document['title']}》可作为{document['category']}方向的直接材料。"
        )
    return takeaways


def _build_evidence_boundary(analysis: dict, matches: list[dict]) -> str:
    evidence_types = {infer_evidence_type(document) for document in matches}
    if len(matches) <= 2:
        return "当前回答基于较少的库内材料，结论应按线索性判断理解。"
    if analysis["years"]:
        return f"当前回答优先使用了{analysis['years'][0]}年的库内材料，未主动扩展到其他年份。"
    if len(evidence_types) == 1:
        evidence_type = next(iter(evidence_types))
        return f"当前证据主要来自单一类型材料（{evidence_type}），仍可继续补充其他类型来源交叉验证。"
    return "当前回答基于现有命中材料归纳，未覆盖库内所有可能相关文本。"


def _score(document: dict, analysis: dict) -> int:
    haystack = " ".join(
        [document.get("title", ""), document.get("category", ""), document.get("content_text", "")]
    )
    score = 0
    thematic_score = 0
    evidence_type = infer_evidence_type(document)
    published_at = _parse_published_at(document.get("published_at", ""))
    if analysis["category_hits"]:
        if document.get("category") in analysis["category_hits"]:
            score += 12
            if any(category in haystack for category in analysis["category_hits"]):
                score += 6
            else:
                score -= 3
        else:
            score -= 4

    if analysis["years"]:
        if any(document.get("published_at", "").startswith(year) for year in analysis["years"]):
            score += 8
        elif any(year in haystack for year in analysis["years"]):
            score += 3
        else:
            score -= 2

    if analysis["relative_start"] and analysis["relative_end"] and published_at:
        start = datetime.strptime(analysis["relative_start"], "%Y-%m-%d").date()
        end = datetime.strptime(analysis["relative_end"], "%Y-%m-%d").date()
        if start <= published_at <= end:
            score += 8
        else:
            score -= 10

    for phrase in analysis["phrases"]:
        if phrase in document.get("title", ""):
            score += 4
        elif phrase in haystack:
            score += 2

    if analysis["domain_hits"]:
        if any(domain in haystack for domain in analysis["domain_hits"]):
            score += 10
        elif analysis["digital_focus"] and _has_broader_heritage_digital_signal(document):
            score += 2
        else:
            score -= 14

    if analysis["digital_focus"]:
        if any(signal in haystack for signal in DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL):
            score += 12
        else:
            score -= 18

    for term in analysis["thematic_terms"]:
        if term in document.get("title", ""):
            thematic_score += max(2, len(term))
        elif term in haystack:
            thematic_score += max(1, len(term) - 1)

    score += thematic_score
    if analysis["thematic_terms"] and thematic_score == 0:
        score -= 12

    task_type = analysis["task_type"]
    if task_type == "concept":
        if evidence_type == "报告资源":
            score += 14
        elif evidence_type == "书刊资讯":
            score += 8
        elif evidence_type == "会议新闻":
            score -= 8
        elif evidence_type == "政策动态":
            score += 2
    elif task_type == "trend":
        if evidence_type == "报告资源":
            score += 10
        elif evidence_type == "书刊资讯":
            score += 5
        elif evidence_type == "政策动态":
            score += 6
        elif evidence_type == "会议新闻":
            score -= 2
    elif task_type == "case":
        if evidence_type == "一般动态":
            score += 8
        elif evidence_type == "政策动态":
            score += 8
        elif evidence_type == "报告资源":
            score += 4
        elif evidence_type == "会议新闻":
            score -= 6
    else:
        if evidence_type == "政策动态":
            score += 10
        elif evidence_type == "会议新闻":
            score += 6
        elif evidence_type == "报告资源":
            score += 2

    if task_type == "trend" and any(signal in haystack for signal in DIGITAL_HIGH_SIGNAL):
        score += 8

    return score


def _format_title_link(document: dict) -> str:
    return f"[{document['title']}]({document['source_url']})"


def _load_documents(library_path: Path) -> list[dict]:
    documents = []
    with library_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                documents.append(json.loads(line))
    return documents


def _rank_documents(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> tuple[list[dict], dict]:
    documents = _load_documents(library_path)
    if reference_date is None:
        reference_date = date.today()

    analysis = _analyze_question(question, documents, reference_date)
    ranked = sorted(
        ((document, _score(document, analysis)) for document in documents),
        key=lambda item: (item[1], item[0].get("published_at", "")),
        reverse=True,
    )
    positive_matches = [document for document, score in ranked if score > 0]
    if analysis["digital_focus"]:
        digital_filtered = [document for document in positive_matches if _has_digital_signal(document)]
        if digital_filtered:
            positive_matches = digital_filtered
    if analysis["relative_start"] and analysis["relative_end"]:
        start = datetime.strptime(analysis["relative_start"], "%Y-%m-%d").date()
        end = datetime.strptime(analysis["relative_end"], "%Y-%m-%d").date()
        relative_filtered = []
        for document in positive_matches:
            published_at = _parse_published_at(document.get("published_at", ""))
            if published_at and start <= published_at <= end:
                relative_filtered.append(document)
        if relative_filtered:
            positive_matches = relative_filtered
    if analysis["years"]:
        year_filtered = [
            document
            for document in positive_matches
            if any(document.get("published_at", "").startswith(year) for year in analysis["years"])
        ]
        matches = year_filtered[:limit] if year_filtered else positive_matches[:limit]
    else:
        matches = positive_matches[:limit]
    return matches, analysis


def answer_question(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> str:
    matches, analysis = _rank_documents(question, library_path, limit=limit, reference_date=reference_date)

    if not matches:
        return "当前库内没有足够材料支持该回答。"

    conclusion = _build_conclusion(question, analysis, matches)
    lines = [
        "基于库内文章归纳：",
        f"问题理解：{question}",
        "",
        "库内结论：",
        conclusion,
        "",
        "证据文章：",
    ]
    for document in matches:
        lines.append(
            f"- [{infer_evidence_type(document)}] {_format_title_link(document)} | {document['published_at']} | {document['category']} | {document['source_url']}"
        )
    lines.extend(["", "可直接用于写作的归纳："])
    for takeaway in _build_takeaways(conclusion, matches):
        lines.append(f"- {takeaway}")
    lines.extend(["", "证据边界：", _build_evidence_boundary(analysis, matches)])
    return "\n".join(lines)


def collect_source_cards(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[dict]:
    matches, _analysis = _rank_documents(question, library_path, limit=limit, reference_date=reference_date)
    return [
        {
            "title": document["title"],
            "url": document["source_url"],
            "published_at": document["published_at"],
            "category": document["category"],
            "evidence_type": infer_evidence_type(document),
        }
        for document in matches
    ]
