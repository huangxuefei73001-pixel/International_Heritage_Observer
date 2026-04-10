from __future__ import annotations

from pathlib import Path

from guoji_yichan_guancha.query import _build_evidence_boundary, _build_takeaways, _format_title_link
from guoji_yichan_guancha.query import _rank_documents, _build_conclusion, infer_evidence_type


def answer_from_library(question: str, library_path: Path) -> dict:
    matches, analysis = _rank_documents(question, library_path, limit=5)

    if not matches:
        return {
            "answer": "当前库内没有足够材料支持该回答。",
            "sources": [],
        }

    conclusion = _build_conclusion(question, analysis, matches)
    answer_lines = [
        "基于库内文章归纳：",
        f"问题理解：{question}",
        "",
        "库内结论：",
        conclusion,
        "",
        "证据文章：",
    ]
    for document in matches:
        answer_lines.append(
            f"- [{infer_evidence_type(document)}] {_format_title_link(document)} | {document['published_at']} | {document['category']} | {document['source_url']}"
        )
    answer_lines.extend(["", "可直接用于写作的归纳："])
    for takeaway in _build_takeaways(conclusion, matches):
        answer_lines.append(f"- {takeaway}")
    answer_lines.extend(["", "证据边界：", _build_evidence_boundary(analysis, matches)])

    return {
        "answer": "\n".join(answer_lines),
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
