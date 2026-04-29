from __future__ import annotations

import json
import logging
import re
import subprocess
from difflib import SequenceMatcher
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


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
PRIMARY_THEME_GROUPS = (
    ("城市韧性", ("城市韧性", "urban resilience", "resilience")),
    ("灾害风险治理", ("灾害风险治理", "disaster risk governance", "disaster risk")),
    ("灾害治理", ("灾害治理", "disaster governance", "风险治理", "灾害")),
)
CASE_CARRIER_TERMS = ("世界遗产地", "世界遗产", "heritage site", "遗产地")
CASE_REQUEST_TERMS = ("案例", "例子", "实践", "遗产地", "world heritage site", "case", "example")
REGISTRY_FIELD_TERMS = ("列入年份", "年份", "国家", "类型", "页面", "网址", "链接", "名录", "官网")
REGISTRY_TYPE_TERMS = {
    "cultural": ("文化遗产", "cultural"),
    "natural": ("自然遗产", "natural"),
    "mixed": ("混合遗产", "mixed"),
}
REGISTRY_EXAMPLE_TERMS = ("例子", "案例", "有哪些", "列表", "名录", "示例")
REGISTRY_COUNT_TERMS = ("多少处", "多少个", "一共有多少", "共有多少", "有多少处", "有多少个")
REGISTRY_COUNTRY_ALIASES = {
    "中国": "China",
    "意大利": "Italy",
    "法国": "France",
    "西班牙": "Spain",
    "德国": "Germany",
    "英国": "United Kingdom",
    "日本": "Japan",
    "韩国": "Republic of Korea",
    "美国": "United States of America",
    "加拿大": "Canada",
    "澳大利亚": "Australia",
    "印度": "India",
    "巴西": "Brazil",
    "墨西哥": "Mexico",
    "埃及": "Egypt",
    "希腊": "Greece",
    "俄罗斯": "Russian Federation",
    "土耳其": "Türkiye",
}
REGISTRY_SITE_PATTERNS = (
    re.compile(r"(?P<name>[\u4e00-\u9fffA-Za-z·\-\s]{2,40})的(?:列入年份|年份|类型|国家|页面|网址|链接)"),
    re.compile(r"(?P<name>[\u4e00-\u9fffA-Za-z·\-\s]{2,40})是什么时候列入"),
    re.compile(r"(?P<name>[\u4e00-\u9fffA-Za-z·\-\s]{2,40})是(?:什么类型|哪一年列入)"),
)
REGISTRY_COLLECTION_PAGE_SIZE = 100
REGISTRY_COLLECTION_MAX_RECORDS = 400
REGISTRY_COUNTRY_PATTERNS = (
    re.compile(r"(?P<country>[\u4e00-\u9fffA-Za-z·\-\s]{2,30})有哪些世界遗产"),
    re.compile(r"(?P<country>[\u4e00-\u9fffA-Za-z·\-\s]{2,30})的世界遗产(?:地)?(?:有哪些|列表|名录|例子|案例)"),
    re.compile(r"(?P<country>[\u4e00-\u9fffA-Za-z·\-\s]{2,30})一共有多少(?:处|个)世界遗产(?:地)?"),
    re.compile(r"(?P<country>[\u4e00-\u9fffA-Za-z·\-\s]{2,30})有多少(?:处|个)世界遗产(?:地)?"),
)
REGISTRY_NOISE_TERMS = (
    "我需要找",
    "我想找",
    "请问",
    "帮我",
    "一下",
    "哪些",
    "有哪些",
    "世界遗产地",
    "世界遗产",
    "遗产地",
    "案例",
    "例子",
    "名录",
    "信息",
    "官网",
    "页面",
    "网址",
    "链接",
    "列入年份",
    "年份",
    "类型",
    "国家",
)
REGISTRY_SELECT_FIELDS = ",".join(
    (
        "id_no",
        "name_en",
        "name_zh",
        "states_names",
        "date_inscribed",
        "category",
    )
)
RISK_SCENE_OPTIONS = {
    "A": {
        "label": "洪水 / 海平面上升",
        "terms": ("洪水", "海平面上升", "flood", "sea level rise", "coastal risk", "lagoon", "water"),
        "follow_up": (
            "1. 泻湖 / 港口城市与海平面上升",
            "2. 洪水防御、排水系统与城市遗产",
            "3. 风暴潮、海岸侵蚀与沿海风险",
        ),
    },
    "B": {
        "label": "火灾 / 林火",
        "terms": ("火灾", "林火", "fire", "wildfire", "combustion", "emergency protection"),
        "follow_up": (
            "1. 历史城区火灾与应急疏散",
            "2. 林火对文化景观 / 木构遗产的影响",
            "3. 火后恢复与长期风险管理",
        ),
    },
    "C": {
        "label": "战争 / 突发灾害",
        "terms": ("战争", "突发灾害", "conflict", "war", "emergency", "post-disaster protection"),
        "follow_up": (
            "1. 战争冲突中的遗产地应急保护",
            "2. 震后 / 灾后抢救与恢复",
            "3. 危机时期的治理协调机制",
        ),
    },
    "D": {
        "label": "城市更新与长期风险治理",
        "terms": ("城市更新与长期风险治理", "urban renewal", "long-term risk", "governance", "planning", "adaptation"),
        "follow_up": (
            "1. 城市更新与遗产地长期韧性",
            "2. 规划管控与风险治理工具",
            "3. 适应性治理与长期管理机制",
        ),
    },
}
RISK_SCENE_MARKER_PREFIX = "风险场景"
RISK_SCENE_DETAIL_OPTIONS = {
    "A": {
        "1": {
            "label": "泻湖 / 港口城市与海平面上升",
            "terms": ("lagoon", "port city", "sea level rise", "coastal flooding", "tidal water"),
            "follow_up": (
                "a. 你更想看泻湖城市本体的水位风险，还是港口防洪设施？",
                "b. 你更偏向威尼斯一类滨水历史城市，还是更广义的沿海港口遗产地？",
            ),
        },
        "2": {
            "label": "洪水防御、排水系统与城市遗产",
            "terms": ("flood defense", "drainage", "water management", "historic urban fabric"),
            "follow_up": (
                "a. 你更想看防洪工程本身，还是历史城区排水系统的适应性改造？",
                "b. 你更偏向城市基础设施治理，还是遗产本体保护与排水冲突？",
            ),
        },
        "3": {
            "label": "风暴潮、海岸侵蚀与沿海风险",
            "terms": ("storm surge", "coastal erosion", "shoreline risk", "coastal adaptation"),
            "follow_up": (
                "a. 你更想看风暴潮冲击，还是海岸侵蚀对遗产边界的长期影响？",
                "b. 你更偏向沿海适应策略，还是岸线风险监测与管理？",
            ),
        },
    },
    "B": {
        "1": {
            "label": "历史城区火灾与应急疏散",
            "terms": ("historic district fire", "urban evacuation", "fire emergency", "historic city"),
            "follow_up": (
                "a. 你更想看应急疏散体系，还是火灾后恢复流程？",
                "b. 你更偏向城市街区层面，还是单体建筑层面？",
            ),
        },
        "2": {
            "label": "林火对文化景观 / 木构遗产的影响",
            "terms": ("wildfire", "cultural landscape", "timber heritage", "forest fire"),
            "follow_up": (
                "a. 你更关注文化景观整体，还是木构遗产防火？",
                "b. 你更想看火前防范，还是火后恢复？",
            ),
        },
        "3": {
            "label": "火后恢复与长期风险管理",
            "terms": ("post-fire recovery", "long-term fire risk", "risk management", "recovery"),
            "follow_up": (
                "a. 你更想看恢复机制，还是长期风险治理工具？",
                "b. 你更偏向单个遗产地恢复，还是区域治理经验？",
            ),
        },
    },
    "C": {
        "1": {
            "label": "战争冲突中的遗产地应急保护",
            "terms": ("conflict", "war", "emergency protection", "heritage protection"),
            "follow_up": (
                "a. 你更想看冲突期间的抢救措施，还是国际协调机制？",
                "b. 你更偏向城市遗产，还是考古遗址 / 文化景观？",
            ),
        },
        "2": {
            "label": "震后 / 灾后抢救与恢复",
            "terms": ("post-disaster recovery", "earthquake", "emergency salvage", "recovery"),
            "follow_up": (
                "a. 你更想看震后抢救，还是灾后长期恢复？",
                "b. 你更偏向保护技术，还是治理协调？",
            ),
        },
        "3": {
            "label": "危机时期的治理协调机制",
            "terms": ("crisis governance", "coordination mechanism", "emergency governance", "risk coordination"),
            "follow_up": (
                "a. 你更想看中央-地方协调，还是国际组织协作？",
                "b. 你更偏向制度机制，还是具体应急操作？",
            ),
        },
    },
    "D": {
        "1": {
            "label": "城市更新与遗产地长期韧性",
            "terms": ("urban renewal", "heritage resilience", "long-term resilience", "historic urban area"),
            "follow_up": (
                "a. 你更偏向城市更新政策，还是遗产区适应性改造？",
                "b. 你更想看长期韧性指标，还是规划工具？",
            ),
        },
        "2": {
            "label": "规划管控与风险治理工具",
            "terms": ("planning control", "risk governance tool", "planning", "management tool"),
            "follow_up": (
                "a. 你更想看规划审批工具，还是风险治理评估工具？",
                "b. 你更偏向管理规划，还是缓冲区 / 空间管控？",
            ),
        },
        "3": {
            "label": "适应性治理与长期管理机制",
            "terms": ("adaptive governance", "long-term management", "adaptation", "governance"),
            "follow_up": (
                "a. 你更想看适应性治理框架，还是日常管理机制？",
                "b. 你更偏向机构协作，还是社区参与？",
            ),
        },
    },
}
RISK_SCENE_DETAIL_MARKER_PREFIX = "风险子场景"
THEME_LED_PRIORITY_GROUPS = (
    ("城市韧性", ("城市韧性", "韧性", "urban resilience", "resilience")),
    ("灾害风险", ("灾害", "防灾", "灾害风险", "risk", "风险", "风险管理")),
    ("应急治理", ("应急", "emergency", "治理", "governance", "灾害治理", "风险治理")),
    ("恢复脆弱性", ("恢复", "recovery", "脆弱性", "vulnerability")),
)
THEME_LED_HEADING_PATTERNS = (
    ("城市韧性与风险治理", ("城市韧性", "韧性", "风险治理", "灾害风险治理", "风险管理", "风险")),
    ("灾害应对与应急保护", ("灾害", "防灾", "应急", "应急保护", "灾害治理")),
    ("脆弱性与恢复机制", ("脆弱性", "恢复", "recovery", "vulnerability")),
)
UNESCO_DATA_HUB_RECORDS_URL = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/records"
UNESCO_CORE_FILTER_TERMS = ("resilience", "disaster", "risk", "emergency", "climate", "hazard")
UNESCO_EXACT_RELEVANCE_PATTERNS = {
    "resilience": re.compile(r"\bresilience\b", re.IGNORECASE),
    "adaptation": re.compile(r"\badaptation\b", re.IGNORECASE),
    "recovery": re.compile(r"\brecovery\b", re.IGNORECASE),
    "disaster": re.compile(r"\bdisaster(s)?\b", re.IGNORECASE),
    "risk": re.compile(r"\brisk(s)?\b", re.IGNORECASE),
    "emergency": re.compile(r"\bemergency\b", re.IGNORECASE),
    "climate": re.compile(r"\bclimate(\s+change)?\b", re.IGNORECASE),
    "hazard": re.compile(r"\bhazard(s)?\b", re.IGNORECASE),
    "flood": re.compile(r"\bflood(ing|s)?\b", re.IGNORECASE),
    "fire": re.compile(r"\b(fire|wildfire|wildfires|forest fire|forest fires)\b", re.IGNORECASE),
    "governance": re.compile(r"\bgovernance\b", re.IGNORECASE),
}
UNESCO_THREAT_SIGNALS = ("disaster", "risk", "emergency", "climate", "hazard", "flood", "fire")
UNESCO_RESPONSE_SIGNALS = ("resilience", "adaptation", "recovery", "governance")
UNESCO_STRONG_EVENT_PATTERNS = (
    re.compile(r"\bdestroy(ed|ion)?\b", re.IGNORECASE),
    re.compile(r"\bthreat(ened|s)?\b", re.IGNORECASE),
    re.compile(r"\bconflict\b", re.IGNORECASE),
    re.compile(r"\bwar\b", re.IGNORECASE),
    re.compile(r"\bflood(ing|s)?\b", re.IGNORECASE),
    re.compile(r"\b(fire|wildfire|wildfires|forest fire|forest fires)\b", re.IGNORECASE),
    re.compile(r"\bsea[- ]level\b", re.IGNORECASE),
    re.compile(r"\bclimate change\b", re.IGNORECASE),
)
UNESCO_WEAK_CONTEXT_PATTERNS = (
    "climatic conditions",
    "adaptability and tolerance",
    "animal migrations",
    "hunting strategy",
    "ecological patterns",
)
UNESCO_THEME_EXPANSIONS = {
    "城市韧性": ("resilience", "adaptation", "recovery"),
    "灾害风险治理": ("disaster", "risk", "emergency", "hazard", "climate", "flood", "fire"),
    "灾害治理": ("disaster", "risk", "emergency", "hazard", "climate", "flood", "fire"),
}
UNESCO_THEME_ALIGNMENT = {
    "城市韧性": {"resilience", "adaptation", "recovery", "climate", "risk"},
    "灾害风险治理": {"disaster", "risk", "emergency", "hazard", "flood", "fire", "governance"},
    "灾害治理": {"disaster", "risk", "emergency", "hazard", "flood", "fire", "governance"},
}
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
STRICT_SOURCE_MODE = True
SOURCE_TYPE_KB = "KB"
SOURCE_TYPE_UNESCO_API = "UNESCO_API"
KB_CHANNEL_NAME = "国际遗产观察"
UNESCO_API_IDENTIFIER = "whc001"
ALLOWED_SOURCE_TYPES = (SOURCE_TYPE_KB, SOURCE_TYPE_UNESCO_API)
LOGGER = logging.getLogger(__name__)


def _contains_keyword(text: str, keyword: str) -> bool:
    if re.search(r"[A-Za-z]", keyword):
        return keyword.lower() in text.lower()
    return keyword in text


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def normalize_clarification_option(value: str) -> str | None:
    normalized = value.strip().upper().rstrip("。.、)")
    if normalized in RISK_SCENE_OPTIONS:
        return normalized
    return None


def normalize_follow_up_option(value: str) -> str | None:
    normalized = value.strip().rstrip("。.、)")
    if normalized in {"1", "2", "3"}:
        return normalized
    return None


def inject_risk_scene_option(base_question: str, option: str) -> str:
    option_data = RISK_SCENE_OPTIONS[option]
    scene_terms = " / ".join(option_data["terms"])
    return f"{base_question}\n[{RISK_SCENE_MARKER_PREFIX}{option}] {option_data['label']}：{scene_terms}"


def inject_risk_scene_detail_option(base_question: str, parent_option: str, detail_option: str) -> str:
    detail_data = RISK_SCENE_DETAIL_OPTIONS[parent_option][detail_option]
    detail_terms = " / ".join(detail_data["terms"])
    return (
        f"{base_question}\n"
        f"[{RISK_SCENE_DETAIL_MARKER_PREFIX}{parent_option}-{detail_option}] "
        f"{detail_data['label']}：{detail_terms}"
    )


def _extract_selected_risk_scene_option(question: str) -> str | None:
    marker = re.search(rf"\[{RISK_SCENE_MARKER_PREFIX}([A-D])\]", question)
    if marker:
        return marker.group(1)
    return None


def _extract_selected_risk_scene_detail(question: str) -> tuple[str | None, str | None]:
    marker = re.search(rf"\[{RISK_SCENE_DETAIL_MARKER_PREFIX}([A-D])-([1-3])\]", question)
    if marker:
        return marker.group(1), marker.group(2)
    return None, None


def _extract_risk_scene_terms(question: str, selected_option: str | None) -> list[str]:
    if selected_option:
        return list(RISK_SCENE_OPTIONS[selected_option]["terms"])
    collected = []
    for option_data in RISK_SCENE_OPTIONS.values():
        if any(_contains_keyword(question, term) for term in option_data["terms"]):
            collected.extend(option_data["terms"])
    return list(dict.fromkeys(collected))


def _extract_risk_scene_detail_terms(
    question: str,
    selected_parent_option: str | None,
    selected_detail_option: str | None,
) -> list[str]:
    if (
        selected_parent_option
        and selected_detail_option
        and selected_parent_option in RISK_SCENE_DETAIL_OPTIONS
        and selected_detail_option in RISK_SCENE_DETAIL_OPTIONS[selected_parent_option]
    ):
        return list(RISK_SCENE_DETAIL_OPTIONS[selected_parent_option][selected_detail_option]["terms"])
    collected = []
    for detail_group in RISK_SCENE_DETAIL_OPTIONS.values():
        for detail_data in detail_group.values():
            if any(_contains_keyword(question, term) for term in detail_data["terms"]):
                collected.extend(detail_data["terms"])
    return list(dict.fromkeys(collected))


def detect_document_source_type(document: dict) -> str | None:
    if document.get("channel") == KB_CHANNEL_NAME:
        return SOURCE_TYPE_KB

    source_identifiers = (
        document.get("source_system"),
        document.get("source_api"),
        document.get("dataset_id"),
    )
    if UNESCO_API_IDENTIFIER in source_identifiers:
        return SOURCE_TYPE_UNESCO_API
    return None


def is_document_from_allowed_source(
    document: dict,
    allowed_source_types: tuple[str, ...] = ALLOWED_SOURCE_TYPES,
) -> bool:
    source_type = detect_document_source_type(document)
    return source_type in allowed_source_types


def _filter_documents_by_source_whitelist(
    documents: list[dict],
    strict_source_mode: bool,
) -> list[dict]:
    if not strict_source_mode:
        return documents
    return [document for document in documents if is_document_from_allowed_source(document)]


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
    selected_risk_scene_option = _extract_selected_risk_scene_option(question)
    selected_risk_scene_detail_parent, selected_risk_scene_detail_option = _extract_selected_risk_scene_detail(question)
    risk_scene_terms = _extract_risk_scene_terms(question, selected_risk_scene_option)
    risk_scene_detail_terms = _extract_risk_scene_detail_terms(
        question,
        selected_risk_scene_detail_parent,
        selected_risk_scene_detail_option,
    )
    relative_start, relative_end = _parse_relative_year_window(question, reference_date)
    query_type = classify_query_type(question)
    analysis = {
        "years": years,
        "category_hits": category_hits,
        "domain_hits": domain_hits,
        "phrases": phrases,
        "thematic_terms": thematic_terms,
        "query_type": query_type,
        "task_type": _detect_task_type(question),
        "primary_theme_terms": _extract_primary_theme_terms(question),
        "case_carrier_terms": _extract_case_carrier_terms(question),
        "selected_risk_scene_option": selected_risk_scene_option,
        "risk_scene_terms": risk_scene_terms,
        "selected_risk_scene_detail_parent": selected_risk_scene_detail_parent,
        "selected_risk_scene_detail_option": selected_risk_scene_detail_option,
        "risk_scene_detail_terms": risk_scene_detail_terms,
        "wants_recent": "最近" in question or "动态" in question,
        "relative_start": relative_start,
        "relative_end": relative_end,
        "digital_focus": any(signal in question for signal in DIGITAL_HIGH_SIGNAL),
    }
    analysis["unesco_registry_query"] = _parse_unesco_registry_query(question, analysis)
    return analysis


def _extract_primary_theme_terms(question: str) -> list[str]:
    terms = []
    for normalized_label, keywords in PRIMARY_THEME_GROUPS:
        if _contains_any(question, keywords):
            terms.append(normalized_label)
    return list(dict.fromkeys(terms))


def _extract_case_carrier_terms(question: str) -> list[str]:
    return [term for term in CASE_CARRIER_TERMS if _contains_keyword(question, term)]


def _clean_registry_value(value: str) -> str:
    cleaned = value.strip(" ：:，,。.？?；;（）()[]【】")
    cleaned = re.sub(r"20\d{2}年", " ", cleaned)
    for noise in REGISTRY_NOISE_TERMS:
        cleaned = cleaned.replace(noise, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _contains_chinese(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def _normalize_registry_country_query(country: str | None) -> str | None:
    if not country:
        return None
    return REGISTRY_COUNTRY_ALIASES.get(country, country)


def _registry_escape_like(value: str) -> str:
    return value.replace('"', '\\"')


def _registry_site_name_variants(site_name: str | None) -> list[str]:
    if not site_name:
        return []
    variants = [site_name]
    for pattern in ("及其", "和", "与", "、"):
        if pattern in site_name:
            head = site_name.split(pattern, 1)[0].strip()
            if len(head) >= 2:
                variants.append(head)
    return list(dict.fromkeys(variants))


def _normalize_registry_site_token(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", value.lower())


def _registry_name_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    left_norm = _normalize_registry_site_token(left)
    right_norm = _normalize_registry_site_token(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm in right_norm or right_norm in left_norm:
        return 1.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _extract_registry_type(question: str) -> str | None:
    for normalized, keywords in REGISTRY_TYPE_TERMS.items():
        if _contains_any(question, keywords):
            return normalized
    return None


def _extract_registry_country(question: str) -> str | None:
    for pattern in REGISTRY_COUNTRY_PATTERNS:
        match = pattern.search(question)
        if match:
            country = _clean_registry_value(match.group("country"))
            if country:
                return country
    return None


def _extract_registry_site_name(question: str) -> str | None:
    for pattern in REGISTRY_SITE_PATTERNS:
        match = pattern.search(question)
        if match:
            name = _clean_registry_value(match.group("name"))
            if name:
                return name
    if any(term in question for term in REGISTRY_FIELD_TERMS) and "的" in question:
        candidate = _clean_registry_value(question.split("的", 1)[0])
        if 2 <= len(candidate) <= 40:
            return candidate
    return None


def _parse_unesco_registry_query(question: str, analysis: dict) -> dict:
    site_name = _extract_registry_site_name(question)
    country = _extract_registry_country(question)
    heritage_type = _extract_registry_type(question)
    year = analysis["years"][0] if analysis.get("years") else None
    asks_fields = {
        "year": any(term in question for term in ("列入年份", "年份", "哪一年", "什么时候列入")),
        "country": "国家" in question,
        "type": "类型" in question,
        "url": any(term in question for term in ("页面", "网址", "链接", "官网")),
        "count": any(term in question for term in REGISTRY_COUNT_TERMS),
    }
    general_examples = (
        bool(analysis.get("case_carrier_terms"))
        and not analysis.get("primary_theme_terms")
        and any(term in question for term in REGISTRY_EXAMPLE_TERMS)
    )
    if site_name:
        mode = "entity_lookup"
    elif country or heritage_type or general_examples:
        mode = "collection_query"
    elif year and (any(asks_fields.values()) or country or heritage_type):
        mode = "collection_query"
    else:
        mode = None
    return {
        "mode": mode,
        "site_name": site_name,
        "country": country,
        "heritage_type": heritage_type,
        "inscription_year": year,
        "asks_fields": asks_fields,
        "general_examples": general_examples,
    }


def _primary_focus(question: str, analysis: dict) -> str:
    if analysis.get("primary_theme_terms"):
        if len(analysis["primary_theme_terms"]) >= 2:
            return "与".join(analysis["primary_theme_terms"][:2])
        return analysis["primary_theme_terms"][0]
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
    if _is_theme_led_case_query(analysis):
        return f"{prefix}的重点不在一般性的世界遗产动态，而在于围绕“{focus}”梳理出可支撑案例分析的主题材料。"
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
    has_case_carrier = bool(analysis.get("case_carrier_terms"))
    if analysis.get("primary_theme_terms") and has_case_carrier:
        if scope:
            return f"你问的是一个主题型检索问题，重点是想了解{scope}语境下“{focus}”的相关信息，并把世界遗产地作为案例载体来寻找可用材料。"
        return f"你问的是一个主题型检索问题，重点是想了解“{focus}”的相关信息，并把世界遗产地作为案例载体来寻找可用材料。"
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
    if _is_theme_led_case_query(analysis):
        details = []
        if evidence_mix:
            details.append(f"当前命中的材料类型主要来自{evidence_mix}")
        if category_mix:
            details.append(f"并覆盖{category_mix}等方向")
        if theme_labels:
            details.append(f"可进一步归纳为{theme_labels}三组证据")
        if details:
            return f"基于库内文章归纳，{conclusion} {'，'.join(details)}。"
        return f"基于库内文章归纳，{conclusion}"

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
    if _is_theme_led_case_query(analysis):
        return f"基于库内文章归纳，当前更能支撑“{focus}”这一主题的分组梳理，世界遗产地在这里更适合作为案例承载体而不是主题本身。"
    if analysis["task_type"] == "concept":
        return f"基于库内文章归纳，当前对“{focus}”的解释，主要围绕{theme_labels or '若干代表性线索'}展开。"
    if analysis["task_type"] == "trend":
        return f"基于库内文章归纳，当前“{focus}”的发展，主要沿着{theme_labels or '若干代表性线索'}几条主线推进。"
    if analysis["task_type"] == "case":
        return f"基于库内文章归纳，当前与“{focus}”相关的实践，主要体现为{theme_labels or '若干代表性线索'}几类路径。"
    return f"基于库内文章归纳，当前库内可见的动作，主要落在{theme_labels or '若干代表性线索'}几类方向上。"


def _is_theme_led_case_query(analysis: dict) -> bool:
    return bool(analysis.get("primary_theme_terms")) and bool(analysis.get("case_carrier_terms"))


def _theme_led_group_score(document: dict, keywords: tuple[str, ...]) -> int:
    title = document.get("title", "")
    haystack = _document_haystack(document)
    score = 0
    for keyword in keywords:
        if _contains_keyword(title, keyword):
            score += 10
        elif _contains_keyword(haystack, keyword):
            score += 5
    return score


def _requires_heritage_case_examples(analysis: dict) -> bool:
    return _is_theme_led_case_query(analysis) and analysis["task_type"] == "case"


def _theme_led_heritage_case_score(document: dict, analysis: dict) -> int:
    if not _is_theme_led_case_query(analysis):
        return 0
    haystack = _document_haystack(document)
    theme_score = 0
    for _label, keywords in THEME_LED_PRIORITY_GROUPS:
        theme_score += _theme_led_group_score(document, keywords)
    heritage_score = 0
    for term in analysis.get("case_carrier_terms", []):
        if _contains_keyword(document.get("title", ""), term):
            heritage_score += 8
        elif _contains_keyword(haystack, term):
            heritage_score += 4
    if theme_score <= 0 or heritage_score <= 0:
        return 0
    return theme_score + heritage_score


def _supports_theme_led_heritage_case(document: dict, analysis: dict) -> bool:
    return _theme_led_heritage_case_score(document, analysis) > 0


def _build_case_clarification_question(question: str, analysis: dict) -> str:
    focus = _primary_focus(question, analysis)
    return (
        f"当前库内未检索到与“{focus}”直接对应的世界遗产地案例。\n"
        "请问你更希望缩小到哪一类风险场景？\n"
        "A. 洪水 / 海平面上升\n"
        "B. 火灾 / 林火\n"
        "C. 战争 / 突发灾害\n"
        "D. 城市更新与长期风险治理"
    )


def _select_unesco_mode(question: str, analysis: dict) -> str | None:
    registry_query = analysis.get("unesco_registry_query", {})
    explicit_registry_lookup = bool(
        registry_query.get("site_name")
        or any(registry_query.get("asks_fields", {}).values())
    )
    if explicit_registry_lookup and registry_query.get("mode"):
        return "registry_query"
    if bool(analysis.get("primary_theme_terms")) and bool(analysis.get("case_carrier_terms")):
        return "thematic_case"
    if registry_query.get("mode"):
        return "registry_query"
    return None


def _should_query_unesco_cases(analysis: dict) -> bool:
    return _select_unesco_mode("", analysis) == "thematic_case"


def _expand_unesco_query_terms(analysis: dict) -> list[str]:
    terms = []
    for theme in analysis.get("primary_theme_terms", []):
        terms.extend(UNESCO_THEME_EXPANSIONS.get(theme, ()))
    terms.extend(analysis.get("risk_scene_terms", []))
    terms.extend(analysis.get("risk_scene_detail_terms", []))
    if not terms:
        terms.extend(UNESCO_CORE_FILTER_TERMS)
    return list(dict.fromkeys(terms))


def _normalize_unesco_country(record: dict) -> str:
    states = record.get("states_names")
    if isinstance(states, list):
        return "、".join(str(state) for state in states if state)
    return str(states or "未知")


def _normalize_unesco_url(record: dict) -> str | None:
    site_id = record.get("id_no")
    if site_id:
        return f"https://whc.unesco.org/en/list/{site_id}"
    return None


def _normalize_unesco_category(record: dict) -> str:
    raw_value = record.get("category") or record.get("category_txt") or record.get("category_short") or ""
    lowered = str(raw_value).lower()
    if "mixed" in lowered or "混合" in str(raw_value):
        return "mixed"
    if "natural" in lowered or "自然" in str(raw_value):
        return "natural"
    if "cultural" in lowered or "文化" in str(raw_value):
        return "cultural"
    return str(raw_value or "未知")


def _fetch_unesco_records(params: dict[str, str | int]) -> list[dict]:
    query_params = {"limit": 20, "select": REGISTRY_SELECT_FIELDS}
    query_params.update(params)
    url = f"{UNESCO_DATA_HUB_RECORDS_URL}?{urlencode(query_params, quote_via=quote)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        try:
            result = subprocess.run(
                ["curl", "-L", "--max-time", "20", "-A", "Mozilla/5.0", url],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return []
    return payload.get("results", [])


def _fetch_unesco_records_paginated(params: dict[str, str | int], page_size: int = REGISTRY_COLLECTION_PAGE_SIZE) -> list[dict]:
    records: list[dict] = []
    offset = 0
    while len(records) < REGISTRY_COLLECTION_MAX_RECORDS:
        page_params = dict(params)
        page_params["limit"] = page_size
        page_params["offset"] = offset
        page_results = _fetch_unesco_records(page_params)
        if not page_results:
            break
        records.extend(page_results)
        if len(page_results) < page_size:
            break
        offset += page_size
    return records


def _matches_registry_site_name(record: dict, site_name: str | None) -> bool:
    if not site_name:
        return True
    candidate_names = [str(record.get(field, "")) for field in ("name_zh", "name_en") if record.get(field)]
    for variant in _registry_site_name_variants(site_name):
        for candidate in candidate_names:
            if _registry_name_similarity(variant, candidate) >= 0.72:
                return True
    return False


def _matches_registry_country(record: dict, country: str | None) -> bool:
    if not country:
        return True
    normalized_country = _normalize_registry_country_query(country)
    states = record.get("states_names")
    if isinstance(states, list):
        state_text = " ".join(str(state) for state in states)
    else:
        state_text = str(states or "")
    return normalized_country.lower() in state_text.lower()


def _matches_registry_type(record: dict, heritage_type: str | None) -> bool:
    if not heritage_type:
        return True
    return _normalize_unesco_category(record) == heritage_type


def _matches_registry_year(record: dict, year: str | None) -> bool:
    if not year:
        return True
    return str(record.get("date_inscribed") or "") == str(year)


def _registry_record_matches(record: dict, registry_query: dict) -> bool:
    return (
        _matches_registry_site_name(record, registry_query.get("site_name"))
        and _matches_registry_country(record, registry_query.get("country"))
        and _matches_registry_type(record, registry_query.get("heritage_type"))
        and _matches_registry_year(record, registry_query.get("inscription_year"))
    )


def _build_registry_fetch_params(registry_query: dict) -> list[dict[str, str | int]]:
    requests: list[dict[str, str | int]] = []
    filter_clauses: list[str] = []
    country = _normalize_registry_country_query(registry_query.get("country"))
    heritage_type = registry_query.get("heritage_type")
    inscription_year = registry_query.get("inscription_year")
    site_name = registry_query.get("site_name")

    if country:
        filter_clauses.append(f'states_names like "{_registry_escape_like(country)}"')
    if heritage_type:
        type_label = {"cultural": "Cultural", "natural": "Natural", "mixed": "Mixed"}.get(heritage_type, heritage_type)
        filter_clauses.append(f'category = "{_registry_escape_like(type_label)}"')
    if inscription_year:
        filter_clauses.append(f'date_inscribed = "{inscription_year}"')

    if site_name:
        for variant in _registry_site_name_variants(site_name):
            field = "name_zh" if _contains_chinese(variant) else "name_en"
            clauses = [f'{field} like "%{_registry_escape_like(variant)}%"']
            clauses.extend(filter_clauses)
            requests.append({"where": " and ".join(clauses)})
        requests.append({"q": site_name})

    if filter_clauses and not site_name:
        requests.append({"where": " and ".join(filter_clauses)})
        if country:
            requests.append({"q": country})
        if heritage_type:
            requests.append({"q": heritage_type})

    if registry_query.get("general_examples") and not requests:
        requests.append({"limit": 12})
    if not requests:
        requests.append({})
    return requests


def _normalize_unesco_registry_record(record: dict) -> dict:
    return {
        "site_name": record.get("name_zh") or record.get("name_en") or "未命名遗产地",
        "country": _normalize_unesco_country(record),
        "inscription_year": record.get("date_inscribed"),
        "heritage_type": _normalize_unesco_category(record),
        "unesco_url": _normalize_unesco_url(record),
        "description": record.get("short_description_en") or record.get("description_en") or record.get("justification_en") or "",
    }


def searchWorldHeritageRegistry(registry_query: dict) -> list[dict]:
    deduped_records: dict[str, dict] = {}
    is_collection_mode = registry_query.get("mode") == "collection_query"
    for params in _build_registry_fetch_params(registry_query):
        fetcher = _fetch_unesco_records_paginated if is_collection_mode else _fetch_unesco_records
        for record in fetcher(params):
            record_key = str(record.get("uuid") or record.get("id_no") or record.get("name_en") or record.get("name_zh"))
            if record_key:
                deduped_records[record_key] = record
    matched = [
        _normalize_unesco_registry_record(record)
        for record in deduped_records.values()
        if _registry_record_matches(record, registry_query)
    ]
    matched.sort(key=lambda case: (str(case.get("inscription_year") or ""), case["site_name"]), reverse=False)
    return matched


def _unesco_relevance_text(record: dict) -> str:
    return " ".join(
        str(record.get(field, ""))
        for field in ("description_en", "short_description_en", "justification_en")
        if record.get(field)
    )


def _detect_unesco_signal_hits(relevance_text: str) -> list[str]:
    hits = []
    for label, pattern in UNESCO_EXACT_RELEVANCE_PATTERNS.items():
        if pattern.search(relevance_text):
            hits.append(label)
    return hits


def _normalize_unesco_danger_flag(record: dict) -> bool:
    danger_value = record.get("danger")
    if isinstance(danger_value, bool):
        return danger_value
    if isinstance(danger_value, str):
        return danger_value.strip().lower() in {"true", "1", "y", "yes"}
    return bool(danger_value)


def _has_unesco_strong_event_context(relevance_text: str) -> bool:
    return any(pattern.search(relevance_text) for pattern in UNESCO_STRONG_EVENT_PATTERNS)


def _has_unesco_weak_context(relevance_text: str) -> bool:
    lowered = relevance_text.lower()
    return any(pattern in lowered for pattern in UNESCO_WEAK_CONTEXT_PATTERNS)


def _is_strong_unesco_case_match(record: dict, hits: list[str], relevance_text: str) -> bool:
    threat_hits = [signal for signal in UNESCO_THREAT_SIGNALS if signal in hits]
    response_hits = [signal for signal in UNESCO_RESPONSE_SIGNALS if signal in hits]
    danger_flag = _normalize_unesco_danger_flag(record)
    if not threat_hits:
        return False
    if danger_flag and _has_unesco_strong_event_context(relevance_text):
        return True
    if len(threat_hits) >= 2 and response_hits and not _has_unesco_weak_context(relevance_text):
        return True
    if {"climate", "flood"}.issubset(set(threat_hits)) and response_hits:
        return True
    if {"climate", "risk"}.issubset(set(threat_hits)) and response_hits and not _has_unesco_weak_context(relevance_text):
        return True
    return False


def _matched_unesco_query_themes(analysis: dict | None, hits: list[str]) -> list[str]:
    if not analysis:
        return []
    matched_themes = []
    hit_set = set(hits)
    for theme in analysis.get("primary_theme_terms", []):
        if hit_set.intersection(UNESCO_THEME_ALIGNMENT.get(theme, set())):
            matched_themes.append(theme)
    return matched_themes


def _score_unesco_case_relevance(record: dict, analysis: dict | None, hits: list[str], relevance_text: str) -> tuple[int, str]:
    if not _is_strong_unesco_case_match(record, hits, relevance_text):
        return 0, ""

    danger_flag = _normalize_unesco_danger_flag(record)
    threat_hits = [signal for signal in UNESCO_THREAT_SIGNALS if signal in hits]
    response_hits = [signal for signal in UNESCO_RESPONSE_SIGNALS if signal in hits]
    matched_themes = _matched_unesco_query_themes(analysis, hits)

    if analysis and analysis.get("primary_theme_terms") and not matched_themes:
        return 0, ""

    score = len(threat_hits) * 6 + len(response_hits) * 5 + len(matched_themes) * 12
    if danger_flag:
        score += 10
    if _has_unesco_strong_event_context(relevance_text):
        score += 8
    if not _has_unesco_weak_context(relevance_text):
        score += 4

    reason_parts = []
    if matched_themes:
        reason_parts.append(f"命中主题：{'、'.join(matched_themes)}")
    if threat_hits:
        reason_parts.append(f"风险信号：{' / '.join(threat_hits[:3])}")
    if response_hits:
        reason_parts.append(f"响应信号：{' / '.join(response_hits[:2])}")
    if danger_flag:
        reason_parts.append("处于 UNESCO danger 语境")
    return score, "；".join(reason_parts)


def _filter_unesco_world_heritage_sites(records: list[dict], analysis: dict | None = None) -> list[dict]:
    filtered = []
    for record in records:
        relevance_text = _unesco_relevance_text(record)
        if not relevance_text:
            continue
        matched_terms = _detect_unesco_signal_hits(relevance_text)
        if not matched_terms:
            continue
        if not any(term in matched_terms for term in UNESCO_CORE_FILTER_TERMS):
            continue
        relevance_score, relevance_reason = _score_unesco_case_relevance(record, analysis, matched_terms, relevance_text)
        if relevance_score <= 0:
            continue
        filtered.append(
            {
                "site_name": record.get("name_zh") or record.get("name_en") or "未命名遗产地",
                "country": _normalize_unesco_country(record),
                "inscription_year": record.get("date_inscribed"),
                "unesco_url": _normalize_unesco_url(record),
                "matched_terms": matched_terms,
                "danger_flag": _normalize_unesco_danger_flag(record),
                "relevance_score": relevance_score,
                "relevance_reason": relevance_reason,
            }
        )
    filtered.sort(key=lambda case: (case["relevance_score"], case["inscription_year"] or ""), reverse=True)
    return filtered


def searchWorldHeritageSites(query_terms: list[str], analysis: dict | None = None) -> list[dict]:
    deduped_records: dict[str, dict] = {}
    for term in query_terms:
        for record in _fetch_unesco_records({"q": term}):
            record_key = str(record.get("uuid") or record.get("id_no") or record.get("name_en") or record.get("name_zh"))
            if record_key:
                deduped_records[record_key] = record
    return _filter_unesco_world_heritage_sites(list(deduped_records.values()), analysis=analysis)


def _build_unesco_case_relevance(case: dict, analysis: dict) -> str:
    focus = _primary_focus("", analysis)
    if case.get("relevance_reason"):
        return f"其 UNESCO 官方简介与“{focus}”的关联主要体现在：{case['relevance_reason']}。"
    matched_terms = " / ".join(case.get("matched_terms", [])[:2]) or "相关风险信号"
    return f"其 UNESCO 官方简介中出现了与“{focus}”相关的 {matched_terms} 信号，可作为该主题下的世界遗产地案例。"


def _build_unesco_case_section(cases: list[dict], analysis: dict) -> str:
    lines = ["相关世界遗产地案例（UNESCO）："]
    for case in cases[:4]:
        title = case["site_name"]
        if case.get("unesco_url"):
            title = f"[{title}]({case['unesco_url']})"
        inscription_year = case.get("inscription_year") or "未知"
        lines.append(
            f"- 名称：{title}；国家：{case['country']}；列入年份：{inscription_year}；相关性：{_build_unesco_case_relevance(case, analysis)}"
        )
    return "\n".join(lines)


def _build_unesco_case_clarification_question() -> str:
    return (
        "当前在UNESCO数据中未检索到与该主题直接匹配的世界遗产地案例。\n"
        "请问你希望聚焦哪类风险场景？\n"
        "A. 洪水 / 海平面上升\n"
        "B. 火灾 / 林火\n"
        "C. 战争 / 突发灾害\n"
        "D. 城市更新与长期风险治理"
    )


def _build_unesco_case_follow_up_clarification(analysis: dict) -> str:
    option = analysis.get("selected_risk_scene_option")
    if not option or option not in RISK_SCENE_OPTIONS:
        return _build_unesco_case_clarification_question()
    option_data = RISK_SCENE_OPTIONS[option]
    lines = [
        f"当前在UNESCO数据中仍未检索到与“{option_data['label']}”直接匹配的稳定世界遗产地案例。",
        "如果你愿意，我们可以继续缩小到更具体的一层：",
    ]
    lines.extend(option_data["follow_up"])
    return "\n".join(lines)


def _build_unesco_case_detail_follow_up_clarification(analysis: dict) -> str:
    parent_option = analysis.get("selected_risk_scene_detail_parent")
    detail_option = analysis.get("selected_risk_scene_detail_option")
    if (
        not parent_option
        or not detail_option
        or parent_option not in RISK_SCENE_DETAIL_OPTIONS
        or detail_option not in RISK_SCENE_DETAIL_OPTIONS[parent_option]
    ):
        return _build_unesco_case_follow_up_clarification(analysis)
    detail_data = RISK_SCENE_DETAIL_OPTIONS[parent_option][detail_option]
    lines = [
        f"当前在UNESCO数据中仍未检索到与“{detail_data['label']}”直接匹配的稳定世界遗产地案例。",
        "如果你愿意，我们可以再把范围缩窄一点：",
    ]
    lines.extend(detail_data["follow_up"])
    return "\n".join(lines)


def _build_registry_case_line(case: dict) -> str:
    title = case["site_name"]
    if case.get("unesco_url"):
        title = f"[{title}]({case['unesco_url']})"
    inscription_year = case.get("inscription_year") or "未知"
    heritage_type = case.get("heritage_type") or "未知"
    return (
        f"- 名称：{title}；国家：{case['country']}；列入年份：{inscription_year}；"
        f"类型：{heritage_type}；UNESCO 页面：{case.get('unesco_url') or '未提供'}"
    )


def _build_unesco_registry_answer(question: str, analysis: dict, registry_query: dict, cases: list[dict]) -> str:
    site_name = registry_query.get("site_name")
    country = registry_query.get("country")
    heritage_type = registry_query.get("heritage_type")
    year = registry_query.get("inscription_year")
    asks_fields = registry_query.get("asks_fields", {})

    lines = ["UNESCO 世界遗产名录信息：", ""]
    if site_name and cases:
        case = cases[0]
        if asks_fields.get("year"):
            lines.append(f"- {case['site_name']}的列入年份：{case.get('inscription_year') or '未知'}")
        elif asks_fields.get("type"):
            lines.append(f"- {case['site_name']}的类型：{case.get('heritage_type') or '未知'}")
        elif asks_fields.get("country"):
            lines.append(f"- {case['site_name']}所在国家：{case['country']}")
        elif asks_fields.get("url"):
            lines.append(f"- {case['site_name']}的 UNESCO 页面：{case.get('unesco_url') or '未提供'}")
        else:
            lines.append(f"- 名称：{case['site_name']}")
        lines.append(_build_registry_case_line(case))
        return "\n".join(lines)

    if country or heritage_type or year or registry_query.get("general_examples"):
        descriptor_parts = []
        if country:
            descriptor_parts.append(country)
        if heritage_type:
            type_label = {"cultural": "文化遗产", "natural": "自然遗产", "mixed": "混合遗产"}.get(heritage_type, heritage_type)
            descriptor_parts.append(type_label)
        if year:
            descriptor_parts.append(f"{year}年列入")
        descriptor = "、".join(descriptor_parts) if descriptor_parts else "相关"
        total_count = len(cases)
        if asks_fields.get("count"):
            lines.append(f"- {descriptor}世界遗产地数量：{total_count}处")
        lines.append(f"- 检索范围：{descriptor}世界遗产地（共{total_count}处）")
        for case in cases:
            lines.append(_build_registry_case_line(case))
        return "\n".join(lines)

    lines.append(f"- 当前问题“{question.rstrip('？?')}”未触发明确的名录字段展示。")
    for case in cases:
        lines.append(_build_registry_case_line(case))
    return "\n".join(lines)


def _theme_led_evidence_sections(documents: list[dict]) -> list[dict]:
    section_map = {label: [] for label, _keywords in THEME_LED_HEADING_PATTERNS}
    for document in documents:
        haystack = _document_haystack(document)
        best_label = None
        best_score = 0
        for label, keywords in THEME_LED_HEADING_PATTERNS:
            score = sum(1 for keyword in keywords if _contains_keyword(haystack, keyword))
            if score > best_score:
                best_score = score
                best_label = label
        if best_label and best_score > 0:
            section_map[best_label].append(document)
    sections = []
    for label, _keywords in THEME_LED_HEADING_PATTERNS:
        if section_map[label]:
            sections.append({"label": label, "documents": section_map[label]})
    if sections:
        return sections
    return [{"label": "核心证据", "documents": documents[:3]}]


def _theme_led_section_summary(label: str, documents: list[dict]) -> str:
    titles = "、".join(f"《{document['title']}》" for document in documents[:2])
    if label == "城市韧性与风险治理":
        return f"从{titles}看，命中的材料更集中在城市韧性、灾害风险与治理框架的耦合，而不是一般性的遗产动态。"
    if label == "灾害应对与应急保护":
        return f"从{titles}看，命中的材料把灾害应对、应急保护与遗产地管理机制放在同一条实践链路里。"
    if label == "脆弱性与恢复机制":
        return f"从{titles}看，命中的材料更强调风险暴露、脆弱性评估与灾后恢复之间的连续关系。"
    return f"从{titles}看，当前命中的材料可作为这一主题下的直接证据。"


def _build_theme_led_answer(question: str, analysis: dict, matches: list[dict], extended_matches: list[dict]) -> str:
    sections = _theme_led_evidence_sections(extended_matches or matches)
    lines = [
        "基于库内文章归纳：",
        "",
        "问题理解：",
        _build_question_understanding(question, analysis),
        "",
        "库内结论：",
        _build_library_conclusion_text(question, analysis, extended_matches or matches, sections),
        "",
    ]
    for section in sections:
        lines.extend([f"{section['label']}：", f"- {_theme_led_section_summary(section['label'], section['documents'])}", ""])
    lines.extend(["证据文章："])
    for document in matches:
        lines.append(
            f"- [{infer_evidence_type(document)}] {_format_title_link(document)} | {document['published_at']} | {document['category']}"
        )
    lines.extend(["", "证据边界：", _build_evidence_boundary(analysis, extended_matches or matches)])
    return "\n".join(lines)


def build_structured_answer(question: str, analysis: dict, matches: list[dict], extended_matches: list[dict] | None = None) -> str:
    if _is_theme_led_case_query(analysis):
        return _build_theme_led_answer(question, analysis, matches, extended_matches or matches)
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
    is_theme_led = _is_theme_led_case_query(analysis)
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
            score += 3 if is_theme_led else 10
        elif analysis["digital_focus"] and _has_broader_heritage_digital_signal(document):
            score += 2
        elif not is_theme_led:
            score -= 14

    if analysis["digital_focus"]:
        if any(signal in haystack for signal in DIGITAL_HIGH_SIGNAL + DIGITAL_BROAD_SIGNAL):
            score += 12
        else:
            score -= 18

    if is_theme_led:
        for label, keywords in THEME_LED_PRIORITY_GROUPS:
            group_score = _theme_led_group_score(document, keywords)
            if label in analysis.get("primary_theme_terms", []):
                thematic_score += group_score * 2
            else:
                thematic_score += group_score
        for term in analysis.get("risk_scene_terms", []):
            if _contains_keyword(document.get("title", ""), term):
                thematic_score += 8
            elif _contains_keyword(haystack, term):
                thematic_score += 4
        for term in analysis.get("risk_scene_detail_terms", []):
            if _contains_keyword(document.get("title", ""), term):
                thematic_score += 10
            elif _contains_keyword(haystack, term):
                thematic_score += 5
        if thematic_score == 0:
            thematic_score -= 20
        case_constraint_score = 0
        for term in analysis.get("case_carrier_terms", []):
            if _contains_keyword(document.get("title", ""), term):
                case_constraint_score += 4
            elif _contains_keyword(haystack, term):
                case_constraint_score += 2
        thematic_score += case_constraint_score
        heritage_case_score = _theme_led_heritage_case_score(document, analysis)
        if heritage_case_score > 0:
            thematic_score += heritage_case_score
        if case_constraint_score > 0 and thematic_score <= case_constraint_score:
            thematic_score -= 10
    else:
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
            score += 2 if is_theme_led else 8
        elif evidence_type == "政策动态":
            score += 2 if is_theme_led else 8
        elif evidence_type == "报告资源":
            score += 12 if is_theme_led else 4
        elif evidence_type == "会议新闻":
            score -= 2 if is_theme_led else -6
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


def _select_relevant_matches_from_ranked(ranked: list[tuple[dict, int]], analysis: dict) -> list[dict]:
    is_theme_led = _is_theme_led_case_query(analysis)
    positive_matches = [document for document, score in ranked if score > 0]
    candidate_matches = [document for document, _score in ranked] if is_theme_led else positive_matches
    if analysis["digital_focus"]:
        digital_filtered = [document for document in candidate_matches if _has_digital_signal(document)]
        if digital_filtered:
            candidate_matches = digital_filtered
    if analysis["relative_start"] and analysis["relative_end"]:
        start = datetime.strptime(analysis["relative_start"], "%Y-%m-%d").date()
        end = datetime.strptime(analysis["relative_end"], "%Y-%m-%d").date()
        relative_filtered = []
        for document in candidate_matches:
            published_at = _parse_published_at(document.get("published_at", ""))
            if published_at and start <= published_at <= end:
                relative_filtered.append(document)
        if relative_filtered:
            candidate_matches = relative_filtered
    if analysis["years"]:
        year_filtered = [
            document
            for document in candidate_matches
            if any(document.get("published_at", "").startswith(year) for year in analysis["years"])
        ]
        candidate_matches = year_filtered if year_filtered else candidate_matches
    return _dedupe_documents(candidate_matches)


def _select_matches_from_ranked(ranked: list[tuple[dict, int]], analysis: dict, limit: int) -> tuple[list[dict], list[dict]]:
    extended_matches = _select_relevant_matches_from_ranked(ranked, analysis)
    if _requires_heritage_case_examples(analysis):
        case_matches = [document for document in extended_matches if _supports_theme_led_heritage_case(document, analysis)]
        case_keys = {_document_key(document) for document in case_matches}
        ordered_matches = case_matches + [document for document in extended_matches if _document_key(document) not in case_keys]
        return ordered_matches[:limit], extended_matches
    return extended_matches[:limit], extended_matches


def _rank_documents_from_loaded_documents(
    question: str,
    documents: list[dict],
    limit: int = 5,
    reference_date: date | None = None,
) -> tuple[list[dict], list[dict], dict]:
    if reference_date is None:
        reference_date = date.today()
    analysis = _analyze_question(question, documents, reference_date)
    ranked = sorted(
        ((document, _score(document, analysis)) for document in documents),
        key=lambda item: (item[1], item[0].get("published_at", "")),
        reverse=True,
    )
    matches, extended_matches = _select_matches_from_ranked(ranked, analysis, limit)
    return matches, extended_matches, analysis


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
    matches, extended_matches = _select_matches_from_ranked(ranked, analysis, max(limit * 2, 8))
    if route_kind == "theory":
        route_filtered = [document for document in extended_matches if _supports_strong_theory_document(document)]
        return _dedupe_documents(route_filtered)[:limit]
    else:
        route_filtered = [document for document in extended_matches if _supports_practice_document(document)]
        if route_filtered:
            route_keys = {_document_key(document) for document in route_filtered}
            extended_matches = route_filtered + [document for document in extended_matches if _document_key(document) not in route_keys]
        return _limit_homogeneous_practice_documents(extended_matches)[:limit]


def _select_answer_context(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
    strict_source_mode: bool = STRICT_SOURCE_MODE,
) -> dict:
    documents = _filter_documents_by_source_whitelist(
        _load_documents(library_path),
        strict_source_mode=strict_source_mode,
    )
    matches, extended_matches, analysis = _rank_documents_from_loaded_documents(
        question,
        documents,
        limit=limit,
        reference_date=reference_date,
    )
    if analysis["query_type"] != "theory_practice_review":
        return {
            "analysis": analysis,
            "matches": matches,
            "extended_matches": extended_matches,
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
        "extended_matches": _dedupe_documents(extended_matches + theory_matches + practice_matches),
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
    strict_source_mode: bool = STRICT_SOURCE_MODE,
) -> dict:
    context = _select_answer_context(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
        strict_source_mode=strict_source_mode,
    )
    matches = context["matches"]
    analysis = context["analysis"]
    unesco_mode = _select_unesco_mode(question, analysis)
    if unesco_mode == "registry_query":
        registry_query = analysis.get("unesco_registry_query", {})
        registry_cases = searchWorldHeritageRegistry(registry_query)
        if not registry_cases:
            return {
                "answer": "当前在UNESCO数据中未检索到相关世界遗产名录信息。",
                "sources": [],
            }
        return {
            "answer": _build_unesco_registry_answer(question, analysis, registry_query, registry_cases),
            "sources": [],
        }
    unesco_cases: list[dict] = []
    unesco_follow_up: str | None = None
    if unesco_mode == "thematic_case":
        unesco_query_terms = _expand_unesco_query_terms(analysis)
        LOGGER.info("UNESCO_QUERY_TERMS=%s", ",".join(unesco_query_terms))
        unesco_cases = searchWorldHeritageSites(unesco_query_terms, analysis=analysis)
        LOGGER.info("UNESCO_RESULTS_COUNT=%s", len(unesco_cases))
        if not unesco_cases:
            if analysis.get("selected_risk_scene_detail_option"):
                unesco_follow_up = _build_unesco_case_detail_follow_up_clarification(analysis)
            elif analysis.get("selected_risk_scene_option"):
                unesco_follow_up = _build_unesco_case_follow_up_clarification(analysis)
            else:
                return {
                    "answer": _build_unesco_case_clarification_question(),
                    "sources": [],
                }
    if not matches:
        if unesco_cases:
            return {
                "answer": "当前知识库未提供相关分析内容。\n\n" + _build_unesco_case_section(unesco_cases, analysis),
                "sources": [],
            }
        if unesco_follow_up:
            return {
                "answer": "当前知识库未提供相关分析内容。\n\n" + unesco_follow_up,
                "sources": [],
            }
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
        answer = build_structured_answer(question, analysis, matches, context.get("extended_matches"))
    if unesco_cases:
        answer = answer + "\n\n" + _build_unesco_case_section(unesco_cases, analysis)
    elif unesco_follow_up:
        answer = answer + "\n\n" + unesco_follow_up
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
    strict_source_mode: bool = STRICT_SOURCE_MODE,
) -> tuple[list[dict], dict]:
    documents = _filter_documents_by_source_whitelist(
        _load_documents(library_path),
        strict_source_mode=strict_source_mode,
    )
    matches, _extended_matches, analysis = _rank_documents_from_loaded_documents(
        question,
        documents,
        limit=limit,
        reference_date=reference_date,
    )
    return matches, analysis


def answer_question(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
    strict_source_mode: bool = STRICT_SOURCE_MODE,
) -> str:
    return build_answer_bundle(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
        strict_source_mode=strict_source_mode,
    )["answer"]


def collect_source_cards(
    question: str,
    library_path: Path,
    limit: int = 5,
    reference_date: date | None = None,
    strict_source_mode: bool = STRICT_SOURCE_MODE,
) -> list[dict]:
    return build_answer_bundle(
        question,
        library_path,
        limit=limit,
        reference_date=reference_date,
        strict_source_mode=strict_source_mode,
    )["sources"]
