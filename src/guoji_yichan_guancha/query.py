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
THEME_DEFINITIONS = [
    ("制度与政策衔接", ("基本法", "法案", "制度", "体制", "改革", "政策", "立法", "国家遗产", "预算", "战略")),
    ("规划与管理工具", ("管理规划", "缓冲区", "规划", "保护区", "区划", "监测", "治理", "景观", "视域")),
    ("影响评估与审批", ("影响评估", "HIA", "审批", "开发", "项目", "补充规划")),
    ("数字化与技术路径", DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL),
    ("阐释与传播", ("阐释", "展示", "传播", "教育", "解释", "解读")),
    ("培训与能力建设", ("培训", "工作坊", "研讨会", "指南", "手册", "能力建设")),
    ("社区与参与", ("社区", "公众", "利益相关者", "参与", "征集意见", "协商")),
    ("国际治理与规则", ("UNESCO", "世界遗产大会", "委员会", "操作指南", "公约", "国际")),
]
THEME_OBSERVATIONS = {
    "制度与政策衔接": "库内更关注国际规则如何转译成国内立法、分类和制度安排。",
    "规划与管理工具": "库内更关注如何把世界遗产要求嵌入管理规划、缓冲区和空间管控工具。",
    "影响评估与审批": "库内更关注国际评估方法如何进入开发审查与审批程序。",
    "数字化与技术路径": "库内更关注数字采集、建模、平台与智能化应用等技术路径。",
    "阐释与传播": "库内更关注如何把价值特征和保护目标转化为公众可理解的阐释语言。",
    "培训与能力建设": "库内更关注通过指南、培训和研讨把国际框架转成实务能力。",
    "社区与参与": "库内更关注利益相关者协商、公众参与和社区角色。",
    "国际治理与规则": "库内更关注委员会、操作指南和国际会议释放出的规则信号。",
    "代表性线索": "库内目前更像是若干代表性线索并行出现，而不是单一方向。",
}
THEME_DIFFICULTIES = {
    "制度与政策衔接": "难点通常在于国际概念需要被翻译成国内法定类别、职责分工和执行机制。",
    "规划与管理工具": "难点通常在于管理规划、缓冲区和既有规划审批体系之间如何真正衔接。",
    "影响评估与审批": "难点通常在于评估方法进入日常审批后是否具备稳定的约束力和可操作性。",
    "数字化与技术路径": "难点通常在于技术展示、长期保存和保护目标之间需要持续平衡。",
    "阐释与传播": "难点通常在于专业价值表述如何转成公众、地方政府和运营者都能理解的语言。",
    "培训与能力建设": "难点通常在于国际术语和方法能否被地方管理者和项目团队稳定掌握。",
    "社区与参与": "难点通常在于不同利益相关方对价值、边界和治理目标的理解并不一致。",
    "国际治理与规则": "难点通常在于国际规则更新节奏与国内执行节奏之间常常存在时间差。",
    "代表性线索": "当前命中的材料仍偏线索性，适合继续围绕其中几条路径深挖。",
}
THEORY_REVIEW_SIGNALS = (
    "理论",
    "框架",
    "范式",
    "讨论成果",
    "成果",
    "进展",
    "participatory governance",
    "people-centred approach",
    "rights-based approach",
    "stakeholder participation",
    "heritage interpretation",
    "values attributes",
    "expert-led",
)
PRACTICE_REVIEW_SIGNALS = (
    "实践",
    "项目",
    "展示",
    "推广",
    "激励",
    "案例征集",
    "奖项",
    "培训",
    "论坛",
    "forum",
    "conference",
    "training",
    "capacity building",
    "handbook",
    "toolkit",
    "award",
    "prize",
    "competition",
    "workshop",
)
REVIEW_SCOPE_SIGNALS = ("近年来", "国际上", "有哪些", "讨论", "成果", "进展")
DUAL_LAYER_SIGNALS = (
    "理论层面",
    "实践层面",
    "理论性的成果",
    "对具体实践",
    "理论和实践",
    "理论与实践",
)
COMPARATIVE_REVIEW_SIGNALS = ("比较", "对比", "差异", "不同国家", "各国", "相比", "横向看")
FACTUAL_LOOKUP_SIGNALS = ("是什么", "怎么界定", "定义", "概念", "何为", "什么意思")
CASE_EXTRACTION_SIGNALS = ("案例", "例子", "项目", "实践", "经验")
TOPIC_SUMMARY_SIGNALS = ("趋势", "动向", "脉络", "进展", "发展", "综述", "研究", "有哪些")
THEORY_ROUTE_TERMS = (
    "participatory governance",
    "people-centred approach",
    "rights-based approach",
    "stakeholder participation",
    "heritage interpretation",
    "values attributes",
    "critique of expert-led management tools",
    "参与式治理",
    "以人为中心",
    "权利本位",
    "利益相关者参与",
    "遗产阐释",
    "价值特征要素",
    "专家主导管理工具反思",
)
PRACTICE_ROUTE_TERMS = (
    "forum",
    "conference",
    "training",
    "capacity building",
    "handbook",
    "toolkit",
    "call for cases",
    "case collection",
    "award",
    "prize",
    "youth programme",
    "competition",
    "community engagement camp",
    "workshop",
    "论坛",
    "会议",
    "培训",
    "能力建设",
    "手册",
    "指南",
    "工具包",
    "案例征集",
    "案例库",
    "奖项",
    "青年项目",
    "竞赛",
    "工作坊",
    "夏令营",
)
THEORY_POINT_PATTERNS = [
    (
        "participatory_governance",
        ("participatory governance", "people-centred approach", "rights-based approach", "以人为中心", "权利本位"),
        "参与式治理、以人为中心与权利本位方法被明确提出为遗产治理的核心框架，社区参与不再只是附属环节",
    ),
    (
        "attributes_interpretation",
        ("heritage interpretation", "values attributes", "遗产阐释", "价值特征要素", "attributes"),
        "价值特征要素与遗产阐释被纳入社区参与讨论，重点转向共同识别、解释和传播遗产价值",
    ),
    (
        "expert_led_critique",
        ("critique of expert-led management tools", "expert-led", "批判反思"),
        "对专家主导型管理工具的反思正在增强，讨论焦点从“有没有工具”转向“谁参与、谁解释、谁决策”",
    ),
]
PRACTICE_POINT_PATTERNS = [
    (
        "training_capacity",
        ("training", "capacity building", "培训", "能力建设", "workshop", "工作坊"),
        "培训与能力建设机制：通过培训、工作坊和能力建设项目，把参与式治理方法转成实践者可操作能力",
    ),
    (
        "handbook_toolkit",
        ("handbook", "toolkit", "手册", "指南", "工具包"),
        "手册、指南与工具包机制：把社区参与要求转译成地方政府、申报团队和管理者可执行的流程工具",
    ),
    (
        "case_collection",
        ("call for cases", "case collection", "案例征集", "案例库"),
        "案例征集与案例库机制：面向不同遗产地公开征集项目，形成可复制的经验样本",
    ),
    (
        "award_incentive",
        ("award", "prize", "奖项"),
        "奖项激励机制：通过国际奖项和表彰，把社区参与项目转成可见、可传播的示范",
    ),
    (
        "youth_programme",
        ("youth programme", "competition", "青年", "竞赛", "community engagement camp", "夏令营"),
        "青年项目与竞赛机制：通过青年论坛、竞赛或专题计划，把社区参与议题前移到下一代实践网络",
    ),
    (
        "forum_display",
        ("forum", "conference", "论坛"),
        "论坛展示与国际会议机制：通过论坛、会议和专题展示，把社区参与案例放进国际同行交流场景",
    ),
]
ANTI_GENERIC_PHRASES = (
    "可从几条线索中提取",
    "当前材料更适合提炼实践路径",
    "更关注",
    "说明这一议题已进入制度调整层面",
    "相关的相关案例",
)
EXPLICIT_THEORY_TERMS = (
    "participatory governance",
    "people-centred approach",
    "rights-based approach",
    "heritage interpretation",
    "values attributes",
    "critique of expert-led management tools",
    "stakeholder participation",
    "参与式治理",
    "以人为中心",
    "权利本位",
    "遗产阐释",
    "价值特征要素",
    "批判反思",
    "专家主导",
    "利益相关者参与",
)
MEETING_OR_TRAINING_TERMS = (
    "论坛",
    "会议",
    "forum",
    "conference",
    "培训",
    "training",
    "workshop",
    "能力建设",
)
HANDBOOK_TITLE_TERMS = ("手册", "指南", "toolkit", "handbook", "工具包")
PRACTICE_TYPE_TERMS = {
    "training_capacity": ("training", "capacity building", "培训", "能力建设", "workshop", "工作坊"),
    "handbook_toolkit": HANDBOOK_TITLE_TERMS,
    "case_collection": ("call for cases", "case collection", "案例征集", "案例库"),
    "award_incentive": ("award", "prize", "奖项"),
    "youth_programme": ("youth programme", "competition", "青年", "竞赛", "community engagement camp", "夏令营"),
    "forum_display": ("forum", "conference", "论坛", "会议"),
}
ORGANIZATION_MARKERS = ("ICCROM", "ICOMOS", "UNESCO", "WHIPIC", "IUCN")


def _contains_keyword(text: str, keyword: str) -> bool:
    if re.search(r"[A-Za-z]", keyword):
        return keyword.lower() in text.lower()
    return keyword in text


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def classify_query_type(question: str) -> str:
    legacy_task_type = _detect_task_type(question)
    has_theory = _contains_any(question, THEORY_REVIEW_SIGNALS)
    has_practice = _contains_any(question, PRACTICE_REVIEW_SIGNALS)
    has_scope = _contains_any(question, REVIEW_SCOPE_SIGNALS)
    has_dual_layer = _contains_any(question, DUAL_LAYER_SIGNALS)
    theory_practice_signal_count = sum((has_theory, has_practice, has_scope, has_dual_layer))

    if theory_practice_signal_count >= 2 and (has_theory or has_dual_layer) and (has_practice or has_dual_layer):
        return "theory_practice_review"
    if _contains_any(question, COMPARATIVE_REVIEW_SIGNALS):
        return "comparative_review"
    if _contains_any(question, FACTUAL_LOOKUP_SIGNALS):
        return "factual_lookup"
    if _contains_any(question, CASE_EXTRACTION_SIGNALS) and legacy_task_type == "case":
        return "case_extraction"
    if _contains_any(question, TOPIC_SUMMARY_SIGNALS) or legacy_task_type == "trend":
        return "topic_summary"
    if legacy_task_type == "concept":
        return "factual_lookup"
    if legacy_task_type == "case":
        return "case_extraction"
    return "topic_summary"


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
    query_type = classify_query_type(question)
    return {
        "years": years,
        "category_hits": category_hits,
        "domain_hits": domain_hits,
        "phrases": phrases,
        "thematic_terms": thematic_terms,
        "query_type": query_type,
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


def _document_haystack(document: dict) -> str:
    return " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            document.get("content_text", ""),
        ]
    )


def _time_scope_phrase(analysis: dict) -> str:
    if analysis["relative_start"] and analysis["relative_end"]:
        return f"{analysis['relative_start'][:4]}—{analysis['relative_end'][:4]}年"
    if analysis["years"]:
        if len(analysis["years"]) == 1:
            return f"{analysis['years'][0]}年"
        return "、".join(f"{year}年" for year in analysis["years"])
    return ""


def _scope_phrase(analysis: dict) -> str:
    parts = []
    time_scope = _time_scope_phrase(analysis)
    if time_scope:
        parts.append(time_scope)
    if analysis["category_hits"]:
        parts.append("、".join(analysis["category_hits"]))
    return "".join(parts)


def _build_question_understanding(question: str, analysis: dict) -> str:
    focus = _primary_focus(question, analysis)
    scope = _scope_phrase(analysis)
    if analysis["task_type"] == "concept":
        if scope:
            return f"你问的是一个概念界定问题，重点不是单条新闻，而是想弄清楚{scope}语境下“{focus}”在库内通常如何被解释。"
        return f"你问的是一个概念界定问题，重点不是单条新闻，而是想弄清楚“{focus}”在库内通常如何被解释。"
    if analysis["task_type"] == "trend":
        if scope:
            return f"你问的是一个趋势梳理问题，重点是想看{scope}围绕“{focus}”有哪些持续出现的线索。"
        return f"你问的是一个趋势梳理问题，重点是想看围绕“{focus}”有哪些持续出现的线索。"
    if analysis["task_type"] == "case":
        if scope:
            return f"你问的是一个案例与实践问题，重点是想从{scope}相关材料中找出与“{focus}”直接相关的代表性做法。"
        return f"你问的是一个案例与实践问题，重点是想从库内材料中找出与“{focus}”直接相关的代表性做法。"
    if scope:
        return f"你问的是一个动态判断问题，重点是想知道{scope}围绕“{focus}”有哪些明确动作或进展。"
    return f"你问的是一个动态判断问题，重点是想知道围绕“{focus}”有哪些明确动作或进展。"


def _format_evidence_mix(matches: list[dict]) -> str:
    evidence_types = []
    for document in matches:
        evidence_type = infer_evidence_type(document)
        if evidence_type not in evidence_types:
            evidence_types.append(evidence_type)
    return "、".join(evidence_types)


def _format_category_mix(matches: list[dict]) -> str:
    categories = []
    for document in matches:
        category = document.get("category", "")
        if category and category not in categories:
            categories.append(category)
    return "、".join(categories[:4])


def _collect_theme_buckets(matches: list[dict]) -> list[dict]:
    buckets = []
    for label, keywords in THEME_DEFINITIONS:
        theme_documents = [document for document in matches if any(keyword in _document_haystack(document) for keyword in keywords)]
        if theme_documents:
            buckets.append({"label": label, "documents": theme_documents})
    if buckets:
        buckets.sort(
            key=lambda item: (len(item["documents"]), max(doc.get("published_at", "") for doc in item["documents"])),
            reverse=True,
        )
        return buckets[:3]
    return [{"label": "代表性线索", "documents": matches[:3]}]


def _theme_titles(documents: list[dict]) -> str:
    return "、".join(f"《{document['title']}》" for document in documents[:2])


def _build_library_conclusion_text(question: str, analysis: dict, matches: list[dict], themes: list[dict]) -> str:
    conclusion = _build_conclusion(question, analysis, matches)
    evidence_mix = _format_evidence_mix(matches)
    category_mix = _format_category_mix(matches)
    theme_labels = "、".join(theme["label"] for theme in themes[:3])

    if analysis["task_type"] == "concept":
        extra = "当前命中的材料更像是从不同类型文本拼出概念边界，而不是给出单一定义。"
    elif analysis["task_type"] == "trend":
        extra = "当前命中的材料更像是几条持续出现的讨论主线，而不是一次性事件。"
    elif analysis["task_type"] == "case":
        extra = "当前命中的材料更适合提炼实践路径和案例线索。"
    else:
        extra = "当前命中的材料更适合判断近期动作集中落在哪些方向。"

    details = []
    if evidence_mix:
        details.append(f"材料类型主要来自{evidence_mix}")
    if category_mix:
        details.append(f"较多落在{category_mix}等方向")
    if theme_labels:
        details.append(f"可归纳为{theme_labels}几条线索")

    if details:
        return f"基于库内文章归纳，{conclusion}{extra} 当前{'，'.join(details)}。"
    return f"基于库内文章归纳，{conclusion}{extra}"


def _build_key_points(themes: list[dict]) -> list[str]:
    points = []
    for theme in themes[:3]:
        label = theme["label"]
        points.append(f"{label}：从{_theme_titles(theme['documents'])}看，{THEME_OBSERVATIONS[label]}")
    return points


def _build_difficulties(themes: list[dict], analysis: dict, matches: list[dict]) -> list[str]:
    difficulties = [THEME_DIFFICULTIES[theme["label"]] for theme in themes[:2]]
    boundary = _build_evidence_boundary(analysis, matches)
    if boundary not in difficulties:
        difficulties.append(boundary)
    return difficulties[:3]


def _describe_document_signal(document: dict) -> str:
    haystack = _document_haystack(document)
    if any(keyword in haystack for keyword in ("基本法", "法案", "制度", "改革", "预算", "战略", "政策")):
        return "说明这一议题已进入制度调整、政策对接或资源配置层面"
    if any(keyword in haystack for keyword in ("指南", "手册")):
        return "把国际规则进一步翻译成地方政府或专业人员可执行的操作语言"
    if any(keyword in haystack for keyword in ("培训", "工作坊", "研讨会", "年会")):
        return "体现当前仍在通过培训、研讨和能力建设推进方法落地"
    if any(keyword in haystack for keyword in ("管理规划", "缓冲区", "规划", "区划", "景观", "视域")):
        return "反映世界遗产要求正在被嵌入既有规划和空间管理工具"
    if any(keyword in haystack for keyword in ("影响评估", "HIA", "审批", "开发")):
        return "反映国际评估工具正在和开发审查、审批程序发生衔接"
    if any(keyword in haystack for keyword in DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL):
        return "展示了数字采集、建模、平台或智能化应用等技术路径"
    if any(keyword in haystack for keyword in ("阐释", "展示", "传播", "教育")):
        return "从阐释与传播角度解释价值特征、展示方式或公众理解"
    return "提供了该议题的直接案例或动态线索"


def _build_practice_points(matches: list[dict]) -> list[str]:
    points = []
    for document in matches[:4]:
        evidence_type = infer_evidence_type(document)
        category = document.get("category", "未分类")
        points.append(
            f"《{document['title']}》({document['published_at']}，{category}，{evidence_type})：{_describe_document_signal(document)}。"
        )
    return points


def _build_single_judgment(question: str, analysis: dict, matches: list[dict], themes: list[dict]) -> str:
    focus = _primary_focus(question, analysis)
    theme_labels = "、".join(theme["label"] for theme in themes[:3])
    if analysis["task_type"] == "concept":
        return f"基于库内文章归纳，当前对“{focus}”的解释，主要围绕{theme_labels or '若干代表性线索'}展开。"
    if analysis["task_type"] == "trend":
        return f"基于库内文章归纳，当前“{focus}”的发展，主要沿着{theme_labels or '若干代表性线索'}几条主线推进。"
    if analysis["task_type"] == "case":
        return f"基于库内文章归纳，当前与“{focus}”相关的实践，主要体现为{theme_labels or '若干代表性线索'}几类路径。"
    return f"基于库内文章归纳，当前库内可见的动作，主要落在{theme_labels or '若干代表性线索'}几类方向上。"


def build_structured_answer(question: str, analysis: dict, matches: list[dict]) -> str:
    themes = _collect_theme_buckets(matches)
    lines = [
        "基于库内文章归纳：",
        "",
        "问题理解：",
        _build_question_understanding(question, analysis),
        "",
        "库内结论：",
        _build_library_conclusion_text(question, analysis, matches, themes),
        "",
        "被关注的要点：",
    ]
    for point in _build_key_points(themes):
        lines.append(f"- {point}")

    lines.extend(["", "难点："])
    for point in _build_difficulties(themes, analysis, matches):
        lines.append(f"- {point}")

    lines.extend(["", "探索实践："])
    for point in _build_practice_points(matches):
        lines.append(f"- {point}")

    lines.extend(["", "如果压缩成一句判断：", _build_single_judgment(question, analysis, matches, themes)])
    lines.extend(["", "证据文章："])
    for document in matches:
        lines.append(
            f"- [{infer_evidence_type(document)}] {_format_title_link(document)} | {document['published_at']} | {document['category']}"
        )
    lines.extend(["", "证据边界：", _build_evidence_boundary(analysis, matches)])
    return "\n".join(lines)


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


def _document_key(document: dict) -> str:
    return document.get("source_url") or document.get("article_id") or document.get("title", "")


def _dedupe_documents(documents: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for document in documents:
        key = _document_key(document)
        if key not in seen:
            deduped.append(document)
            seen.add(key)
    return deduped


def _is_meeting_or_training_document(document: dict) -> bool:
    haystack = _document_haystack(document)
    return infer_evidence_type(document) == "会议新闻" or _contains_any(haystack, MEETING_OR_TRAINING_TERMS)


def _has_explicit_theory_terms(text: str) -> bool:
    return _contains_any(text, EXPLICIT_THEORY_TERMS)


def _supports_theory_document(document: dict) -> bool:
    haystack = _document_haystack(document)
    if not _has_explicit_theory_terms(haystack):
        return False
    if _is_meeting_or_training_document(document):
        return _has_explicit_theory_terms(document.get("content_text", ""))
    return True


def _supports_strong_theory_document(document: dict) -> bool:
    if not _supports_theory_document(document):
        return False
    return infer_evidence_type(document) != "会议新闻"


def _supports_handbook_document(document: dict) -> bool:
    title_haystack = " ".join([document.get("title", ""), document.get("category", "")])
    return _contains_any(title_haystack, HANDBOOK_TITLE_TERMS)


def _practice_type_for_document(document: dict) -> str:
    if _supports_handbook_document(document):
        return "handbook_toolkit"
    haystack = _document_haystack(document)
    for practice_type, keywords in PRACTICE_TYPE_TERMS.items():
        if practice_type == "handbook_toolkit":
            continue
        if _contains_any(haystack, keywords):
            return practice_type
    return "other"


def _organization_bucket(document: dict) -> str:
    title = document.get("title", "")
    category = document.get("category", "")
    haystack = f"{title} {category}"
    for marker in ORGANIZATION_MARKERS:
        if marker.lower() in haystack.lower():
            return marker
    normalized = re.sub(r"[【】\[\]（）()：:《》“”\"'、，,.\-_/]+", " ", title).strip()
    if not normalized:
        return category or "unknown"
    return normalized.split()[0]


def _limit_homogeneous_practice_documents(
    documents: list[dict],
    keep_keys: set[str] | None = None,
    per_bucket_limit: int = 1,
) -> list[dict]:
    limited = []
    bucket_counts = {}
    reserved = set(keep_keys or set())
    for document in documents:
        key = _document_key(document)
        if key in reserved:
            limited.append(document)
            continue
        bucket = (_organization_bucket(document), _practice_type_for_document(document))
        if bucket[1] != "other":
            count = bucket_counts.get(bucket, 0)
            if count >= per_bucket_limit:
                continue
            bucket_counts[bucket] = count + 1
        limited.append(document)
    return _dedupe_documents(limited)


def _supports_practice_document(document: dict) -> bool:
    return _contains_any(_document_haystack(document), PRACTICE_ROUTE_TERMS)


def _select_matches_from_ranked(ranked: list[tuple[dict, int]], analysis: dict, limit: int) -> list[dict]:
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
    return _dedupe_documents(matches)


def _rank_documents_from_loaded_documents(
    question: str,
    documents: list[dict],
    limit: int = 5,
    reference_date: date | None = None,
) -> tuple[list[dict], dict]:
    if reference_date is None:
        reference_date = date.today()
    analysis = _analyze_question(question, documents, reference_date)
    ranked = sorted(
        ((document, _score(document, analysis)) for document in documents),
        key=lambda item: (item[1], item[0].get("published_at", "")),
        reverse=True,
    )
    return _select_matches_from_ranked(ranked, analysis, limit), analysis


def _build_route_question(question: str, route_terms: tuple[str, ...]) -> str:
    return f"{question} {' '.join(route_terms)}"


def _rank_documents_for_route(
    question: str,
    documents: list[dict],
    route_terms: tuple[str, ...],
    route_kind: str,
    limit: int = 6,
    reference_date: date | None = None,
) -> list[dict]:
    if reference_date is None:
        reference_date = date.today()
    expanded_question = _build_route_question(question, route_terms)
    analysis = _analyze_question(expanded_question, documents, reference_date)
    ranked = []
    for document in documents:
        haystack = _document_haystack(document)
        score = _score(document, analysis)
        if route_kind == "theory":
            if _supports_strong_theory_document(document):
                score += 32
            elif _supports_theory_document(document):
                score += 6
            else:
                score -= 8
        else:
            score += 28 if _supports_practice_document(document) else -8
            if infer_evidence_type(document) == "会议新闻":
                score += 4
        for term in route_terms:
            if _contains_keyword(document.get("title", ""), term):
                score += 4
            elif _contains_keyword(haystack, term):
                score += 2
        ranked.append((document, score))
    matches = _select_matches_from_ranked(ranked, analysis, max(limit * 2, 8))
    if route_kind == "theory":
        route_filtered = [document for document in matches if _supports_strong_theory_document(document)]
        return _dedupe_documents(route_filtered)[:limit]
    else:
        route_filtered = [document for document in matches if _supports_practice_document(document)]
        if route_filtered:
            route_keys = {_document_key(document) for document in route_filtered}
            matches = route_filtered + [document for document in matches if _document_key(document) not in route_keys]
        return _limit_homogeneous_practice_documents(matches)[:limit]


def _select_answer_context(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> dict:
    documents = _load_documents(library_path)
    matches, analysis = _rank_documents_from_loaded_documents(
        question,
        documents,
        limit=limit,
        reference_date=reference_date,
    )
    if analysis["query_type"] != "theory_practice_review":
        return {
            "analysis": analysis,
            "matches": matches,
            "theory_matches": [],
            "practice_matches": [],
        }

    theory_matches = _rank_documents_for_route(
        question,
        documents,
        THEORY_ROUTE_TERMS,
        "theory",
        limit=max(limit, 6),
        reference_date=reference_date,
    )
    practice_matches = _rank_documents_for_route(
        question,
        documents,
        PRACTICE_ROUTE_TERMS,
        "practice",
        limit=max(limit, 6),
        reference_date=reference_date,
    )
    merged_matches = _limit_homogeneous_practice_documents(
        theory_matches + practice_matches + matches,
        keep_keys={_document_key(document) for document in theory_matches},
    )[: max(limit, 8)]
    return {
        "analysis": analysis,
        "matches": merged_matches,
        "theory_matches": theory_matches,
        "practice_matches": practice_matches,
    }


def _build_theory_fallback_text(document: dict) -> str:
    haystack = _document_haystack(document)
    if _contains_any(haystack, ("community participation", "社区参与", "stakeholder participation", "利益相关者")):
        return "社区与利益相关者参与被直接纳入遗产治理讨论，不再只作为外围传播议题"
    return "该文直接把社区参与与遗产保护、管理和治理框架放在同一讨论中"


def _build_practice_fallback_text(document: dict) -> str:
    haystack = _document_haystack(document)
    if _contains_any(haystack, ("论坛", "会议", "forum", "conference")):
        return "通过国际论坛或会议展示社区参与案例，并促成同行之间的经验传播"
    if _contains_any(haystack, ("培训", "能力建设", "training", "capacity building", "workshop")):
        return "通过培训和工作坊把参与式治理方法转译成实践者可执行的步骤"
    if _contains_any(haystack, ("奖项", "award", "prize")):
        return "通过奖项表彰强化社区参与项目的可见度和示范效应"
    return "该文展示了社区参与议题如何被转化为国际传播、推广或激励机制"


def _build_route_points(
    documents: list[dict],
    patterns: list[tuple[str, tuple[str, ...], str]],
    fallback_builder,
    minimum: int = 3,
    blocked_keys: set[str] | None = None,
    allow_fallback: bool = True,
) -> tuple[list[dict], set[str]]:
    points = []
    used_keys = set(blocked_keys or set())
    for label, keywords, summary in patterns:
        if label == "handbook_toolkit":
            supporting_documents = [
                document
                for document in documents
                if _document_key(document) not in used_keys and _supports_handbook_document(document)
            ]
        else:
            supporting_documents = [
                document
                for document in documents
                if _document_key(document) not in used_keys and _contains_any(_document_haystack(document), keywords)
            ]
        if supporting_documents:
            document = supporting_documents[0]
            used_keys.add(_document_key(document))
            points.append(
                {
                    "label": label,
                    "text": f"{summary}。支撑文章：{_format_title_link(document)}。",
                }
            )
    if allow_fallback:
        for document in documents:
            if len(points) >= minimum:
                break
            key = _document_key(document)
            if key in used_keys:
                continue
            used_keys.add(key)
            points.append(
                {
                    "label": f"fallback-{len(points) + 1}",
                    "text": f"{fallback_builder(document)}。支撑文章：{_format_title_link(document)}。",
                }
            )
    return points, used_keys


def _build_theory_practice_conclusion(theory_points: list[dict], practice_points: list[dict]) -> str:
    if theory_points and practice_points:
        return (
            f"基于库内文章归纳，这一议题在库内同时呈现出{len(theory_points)}条理论主线和"
            f"{len(practice_points)}类实践机制：理论上，社区参与已经从附属性的公众动员问题，"
            "转向遗产治理框架本身；实践上，国际传播不只靠单点案例，而是通过论坛展示、"
            "能力建设、工具转译、案例征集与奖项激励等机制持续扩散。"
        )
    if theory_points:
        return "基于库内文章归纳，当前材料更能稳定支撑理论层面的梳理，实践机制覆盖相对较弱。"
    if practice_points:
        return "基于库内文章归纳，当前材料更能稳定支撑实践机制层面的梳理，理论框架覆盖相对较弱。"
    return "当前库内没有足够材料支持该回答。"


def _build_theory_practice_takeaways(theory_points: list[dict], practice_points: list[dict]) -> list[str]:
    lines = []
    if len(theory_points) >= 3:
        lines.append("理论部分可概括为“治理框架重组—价值阐释重写—工具反思”三层结构。")
    elif len(theory_points) == 2:
        lines.append("理论部分当前更适合围绕库内已稳定命中的两条主线展开，不宜外推成完整理论框架。")
    elif len(theory_points) == 1:
        lines.append("理论部分当前更稳定支撑一条核心主线，写作时宜按单一理论线索展开，不宜扩写成完整框架。")
    if practice_points:
        lines.append("实践部分可概括为“论坛展示—培训转译—工具手册—案例征集—奖项激励”几类扩散机制。")
    lines.append("如果要写报告，适合用“问题意识—理论进展—转译机制—证据文章”四段结构展开。")
    return lines


def _build_theory_practice_evidence_boundary(
    matches: list[dict],
    theory_points: list[dict],
    practice_points: list[dict],
) -> str:
    lines = []
    if len(theory_points) < 3:
        lines.append(f"库内现有材料对理论层面的覆盖较弱，目前只能稳定支撑{len(theory_points)}条理论归纳。")
    if len(practice_points) < 3:
        lines.append(f"库内现有材料对实践机制层面的覆盖较弱，目前只能稳定支撑{len(practice_points)}类实践机制。")
    if not lines:
        lines.append(
            f"当前回答基于{len(matches)}篇命中文章整理，理论向与实践向材料均有覆盖，但仍不是对库内全文的穷尽检索。"
        )
    return " ".join(lines)


def _compose_theory_practice_review_answer(
    question: str,
    matches: list[dict],
    theory_matches: list[dict],
    practice_matches: list[dict],
    strict: bool = False,
) -> str:
    theory_pool = theory_matches if not strict else _dedupe_documents(theory_matches + matches)
    theory_points, theory_used_keys = _build_route_points(
        theory_pool,
        THEORY_POINT_PATTERNS,
        _build_theory_fallback_text,
        minimum=3,
        allow_fallback=False,
    )
    practice_pool = practice_matches if not strict else _dedupe_documents(practice_matches + matches)
    practice_points, _practice_used_keys = _build_route_points(
        practice_pool,
        PRACTICE_POINT_PATTERNS,
        _build_practice_fallback_text,
        minimum=3,
        blocked_keys=theory_used_keys,
    )
    lines = [
        "基于库内文章归纳：",
        "",
        "问题理解：",
        f"你问的是一个理论与实践并行的综述问题，重点不是单一案例，而是想同时梳理“{question.rstrip('？?')}”所涉及的理论进展，以及这些讨论如何被转成展示、推广和激励性的国际实践机制。",
        "",
        "库内结论：",
        _build_theory_practice_conclusion(theory_points, practice_points),
        "",
        "理论性的成果：",
    ]
    for point in theory_points:
        lines.append(f"- {point['text']}")
    lines.extend(["", "对应的国际性实践机制/项目："])
    for point in practice_points:
        lines.append(f"- {point['text']}")
    lines.extend(["", "可直接用于写作的归纳："])
    for takeaway in _build_theory_practice_takeaways(theory_points, practice_points):
        lines.append(f"- {takeaway}")
    lines.extend(["", "证据文章："])
    for document in matches:
        lines.append(
            f"- [{infer_evidence_type(document)}] {_format_title_link(document)} | {document['published_at']} | {document['category']}"
        )
    lines.extend(
        [
            "",
            "证据边界：",
            _build_theory_practice_evidence_boundary(matches, theory_points, practice_points),
        ]
    )
    return "\n".join(lines)


def _needs_theory_practice_retry(answer: str, theory_matches: list[dict], practice_matches: list[dict]) -> bool:
    if any(phrase in answer for phrase in ANTI_GENERIC_PHRASES):
        return True
    if "理论性的成果：" not in answer or "对应的国际性实践机制/项目：" not in answer:
        return True
    if len(theory_matches) == 0 or len(practice_matches) == 0:
        return True
    return False


def build_theory_practice_review_answer(
    question: str,
    matches: list[dict],
    theory_matches: list[dict],
    practice_matches: list[dict],
) -> str:
    answer = _compose_theory_practice_review_answer(
        question,
        matches,
        theory_matches,
        practice_matches,
        strict=False,
    )
    if _needs_theory_practice_retry(answer, theory_matches, practice_matches):
        answer = _compose_theory_practice_review_answer(
            question,
            matches,
            theory_matches,
            practice_matches,
            strict=True,
        )
    return answer


def build_answer_bundle(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> dict:
    context = _select_answer_context(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
    )
    matches = context["matches"]
    analysis = context["analysis"]
    if not matches:
        return {
            "answer": "当前库内没有足够材料支持该回答。",
            "sources": [],
        }
    if analysis["query_type"] == "theory_practice_review":
        answer = build_theory_practice_review_answer(
            question,
            matches,
            context["theory_matches"],
            context["practice_matches"],
        )
    else:
        answer = build_structured_answer(question, analysis, matches)
    return {
        "answer": answer,
        "sources": [
            {
                "title": document["title"],
                "url": document["source_url"],
                "published_at": document["published_at"],
                "category": document["category"],
                "evidence_type": infer_evidence_type(document),
            }
            for document in matches
        ],
    }


def _rank_documents(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> tuple[list[dict], dict]:
    documents = _load_documents(library_path)
    return _rank_documents_from_loaded_documents(question, documents, limit=limit, reference_date=reference_date)


def answer_question(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> str:
    return build_answer_bundle(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
    )["answer"]


def collect_source_cards(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
) -> list[dict]:
    return build_answer_bundle(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
    )["sources"]
