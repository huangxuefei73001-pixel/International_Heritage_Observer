from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ArticleRecord:
    article_id: str
    title: str
    published_at: str
    channel: str
    category: str
    source_url: str
    local_source_path: str
    content_text: str
    content_html_excerpt: str
    parse_status: str
    tags_auto: list[str]

    def to_document(self) -> dict:
        return asdict(self)
