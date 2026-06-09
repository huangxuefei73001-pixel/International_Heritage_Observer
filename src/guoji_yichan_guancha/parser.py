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


def _clean_markdown_body(markdown_text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown_text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[*_`#-]+\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*[=-]{3,}\s*$", "", text, flags=re.M)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line or line in NOISE_LINES:
            continue
        if line.startswith(("* {", "body {", ".__page_content__", ".title {", ".__meta__", "blockquote.source")):
            continue
        if any(token in line for token in ("阅读![](data:image", "赞 ![](data:image", "分享 ![](data:image", "留言", "推荐")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _pick_markdown_title(markdown_text: str, fallback: str) -> tuple[str, str]:
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip()]
    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(r"[=-]{3,}", lines[index + 1]):
            return line, "ok"
    for line in lines:
        if line.startswith("#"):
            return line.lstrip("# ").strip(), "ok"
    return fallback, "title_fallback"


def _pick_markdown_published_at(markdown_text: str) -> str:
    match = re.search(r"(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2})", markdown_text)
    return match.group(1) if match else ""


def _pick_markdown_channel(markdown_text: str) -> str:
    match = re.search(r"原创\s+(.*?)\s+20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}", markdown_text)
    if not match:
        return "国际遗产观察"
    channel = match.group(1).strip()
    if "国际遗产观察" in channel:
        return "国际遗产观察"
    return channel or "国际遗产观察"


def _pick_markdown_source_url(markdown_text: str) -> str:
    match = re.search(r"原文地址:\s*\[([^\]]+)\]\((https?://[^)]+)\)", markdown_text)
    if match:
        return match.group(2)
    fallback = re.search(r"https://mp\.weixin\.qq\.com/s/[A-Za-z0-9_\-]+", markdown_text)
    return fallback.group(0) if fallback else ""


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


def parse_markdown_article(path: Path, category: str) -> ArticleRecord:
    markdown_text = path.read_text(encoding="utf-8")
    title, parse_status = _pick_markdown_title(markdown_text, path.stem)
    source_url = _pick_markdown_source_url(markdown_text)
    content_text = _clean_markdown_body(markdown_text)
    article_id = hashlib.sha1(f"{path}|{title}".encode("utf-8")).hexdigest()[:16]

    return ArticleRecord(
        article_id=article_id,
        title=title,
        published_at=_pick_markdown_published_at(markdown_text),
        channel=_pick_markdown_channel(markdown_text),
        category=category,
        source_url=source_url,
        local_source_path=str(path),
        content_text=content_text,
        content_html_excerpt=markdown_text[:1200],
        parse_status=parse_status,
        tags_auto=[],
    )
