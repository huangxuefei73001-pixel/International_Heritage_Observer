from __future__ import annotations

import hashlib
import html
import quopri
import re
import zipfile
from pathlib import Path

from .models import ArticleRecord


DOC_MARKER = b"Content-Location: file:///C:/fake/document.html\n\n"
NOISE_LINES = {"阅读", "赞", "分享", "推荐", "留言", "国际遗产观察", "(unknown)"}


def _pick_class(html_text: str, class_name: str) -> str:
    match = re.search(fr'<[^>]+class="{class_name}"[^>]*>(.*?)</[^>]+>', html_text, flags=re.S)
    if not match:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", match.group(1)).strip())


def _clean_body(html_text: str) -> str:
    if "</blockquote>" in html_text:
        html_text = html_text.split("</blockquote>", 1)[1]
    html_text = re.sub(r"<(script|style).*?</\1>", "", html_text, flags=re.S | re.I)
    html_text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.I)
    html_text = re.sub(r"</(p|div|section|h1|h2|h3|li|blockquote|hr)>", "\n", html_text, flags=re.I)
    html_text = re.sub(r"<[^>]+>", "", html_text)
    text = html.unescape(html_text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line and line not in NOISE_LINES)


def parse_docx_article(path: Path, category: str) -> ArticleRecord:
    with zipfile.ZipFile(path) as archive:
        mht = archive.read("word/afchunk.mht")

    if DOC_MARKER not in mht:
        raise ValueError(f"Expected marker not found in {path}")

    body = mht.split(DOC_MARKER, 1)[1].split(b"------=mhtDocumentPart", 1)[0]
    html_text = quopri.decodestring(body).decode("utf-8", errors="ignore")

    raw_title = _pick_class(html_text, "title")
    title = path.stem if not raw_title or raw_title == "(unknown)" else raw_title
    parse_status = "title_fallback" if title == path.stem else "ok"
    url_match = re.search(r'原文地址: <a href="([^"]+)"', html_text)
    content_text = _clean_body(html_text)
    article_id = hashlib.sha1(f"{path}|{title}".encode("utf-8")).hexdigest()[:16]

    return ArticleRecord(
        article_id=article_id,
        title=title,
        published_at=_pick_class(html_text, "create_time"),
        channel=_pick_class(html_text, "nick_name") or "国际遗产观察",
        category=category,
        source_url=url_match.group(1) if url_match else "",
        local_source_path=str(path),
        content_text=content_text,
        content_html_excerpt=html_text[:1200],
        parse_status=parse_status,
        tags_auto=[],
    )
