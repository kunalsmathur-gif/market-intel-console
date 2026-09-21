"""Publisher RSS/Atom feeds — free (PRD §8.4). Headlines, links and short quotes only.

This connector returns raw feed items. Turning a headline into a claim with a
quote-matched, 25-word-capped excerpt (citebell_schemas.Evidence) is the extraction
step's job, not the collector's — a feed item isn't evidence for any specific claim yet.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from citebell_schemas import Source

from .base import DataSourceError, get_with_retries, require

ATOM_NS = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True)
class FeedItem:
    source_id: str
    title: str
    link: str
    summary: str | None
    published_at: datetime | None


def fetch_feed(client: httpx.Client, source: Source) -> list[FeedItem]:
    """Fetch and parse an RSS 2.0, RSS 1.0 (RDF), or Atom feed into plain items."""
    require(source, "rss")
    if not source.url:
        raise DataSourceError(f"RSS source {source.id!r} has no url configured")

    response = get_with_retries(client, source.url)
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise DataSourceError(f"RSS source {source.id!r}: invalid XML: {exc}") from exc

    rss_items = root.findall(".//{*}item")
    if rss_items:
        return [_parse_rss_item(source.id, item) for item in rss_items]
    atom_entries = root.findall(f".//{ATOM_NS}entry")
    if atom_entries:
        return [_parse_atom_entry(source.id, entry) for entry in atom_entries]
    return []


def _text(item: ET.Element, tag: str) -> str | None:
    if not tag.startswith("{"):
        tag = f"{{*}}{tag}"  # match this local name in any namespace (or none) — RSS 1.0/RDF
        # feeds put every element in a default namespace; plain RSS 2.0 has no namespace at all.
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else None


def _parse_rss_item(source_id: str, item: ET.Element) -> FeedItem:
    pub_raw = _text(item, "pubDate")
    return FeedItem(
        source_id=source_id,
        title=_text(item, "title") or "",
        link=_text(item, "link") or "",
        summary=_text(item, "description"),
        published_at=_parse_date(pub_raw) if pub_raw else None,
    )


def _parse_atom_entry(source_id: str, entry: ET.Element) -> FeedItem:
    link_el = entry.find(f"{ATOM_NS}link")
    link = link_el.get("href", "") if link_el is not None else ""
    pub_raw = _text(entry, f"{ATOM_NS}published") or _text(entry, f"{ATOM_NS}updated")
    return FeedItem(
        source_id=source_id,
        title=_text(entry, f"{ATOM_NS}title") or "",
        link=link,
        summary=_text(entry, f"{ATOM_NS}summary"),
        published_at=_parse_date(pub_raw) if pub_raw else None,
    )


def _parse_date(raw: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
