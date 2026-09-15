import httpx
import pytest
import respx

from citebell_schemas import Source, SourceKind, SourceTier
from citebell_worker.data.base import DataSourceError
from citebell_worker.data.rss import fetch_feed

RSS_URL = "https://wire.example/markets.rss"

RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Wire</title>
    <item>
      <title>Nifty closes at a record high</title>
      <link>https://wire.example/story-1</link>
      <description>Benchmark indices rallied on strong FII buying.</description>
      <pubDate>Mon, 15 Sep 2026 10:30:00 +0530</pubDate>
    </item>
    <item>
      <title>RBI holds repo rate steady</title>
      <link>https://wire.example/story-2</link>
      <description>The MPC voted 5-1 to hold.</description>
      <pubDate>Mon, 15 Sep 2026 09:00:00 +0530</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom Wire</title>
  <entry>
    <title>Gold hits fresh high</title>
    <link href="https://wire.example/gold" />
    <summary>Spot gold rose 1.2%.</summary>
    <published>2026-09-15T09:15:00+05:30</published>
  </entry>
</feed>
"""


def rss_source(**kw: object) -> Source:
    fields: dict[str, object] = {
        "id": "example-wire", "name": "Example Wire", "domain": "wire.example",
        "tier": SourceTier.T2, "kind": SourceKind.RSS, "url": RSS_URL,
    }
    return Source.model_validate(fields | kw)


@respx.mock
def test_fetch_feed_parses_rss_2_items() -> None:
    respx.get(RSS_URL).mock(return_value=httpx.Response(200, content=RSS_XML))
    items = fetch_feed(httpx.Client(), rss_source())
    assert [i.title for i in items] == ["Nifty closes at a record high", "RBI holds repo rate steady"]
    assert items[0].link == "https://wire.example/story-1"
    assert items[0].published_at is not None
    assert items[0].published_at.year == 2026


@respx.mock
def test_fetch_feed_parses_atom_entries() -> None:
    respx.get(RSS_URL).mock(return_value=httpx.Response(200, content=ATOM_XML))
    items = fetch_feed(httpx.Client(), rss_source())
    assert len(items) == 1
    assert items[0].title == "Gold hits fresh high"
    assert items[0].link == "https://wire.example/gold"
    assert items[0].published_at is not None


@respx.mock
def test_fetch_feed_raises_on_invalid_xml() -> None:
    respx.get(RSS_URL).mock(return_value=httpx.Response(200, content=b"not xml"))
    with pytest.raises(DataSourceError, match="invalid XML"):
        fetch_feed(httpx.Client(), rss_source())


def test_fetch_feed_requires_a_url() -> None:
    source = rss_source(url=None)
    with pytest.raises(DataSourceError, match="no url"):
        fetch_feed(httpx.Client(), source)


def test_fetch_feed_requires_an_rss_source() -> None:
    api_source = rss_source(kind=SourceKind.API, url=None)
    with pytest.raises(DataSourceError, match="expected 'rss'"):
        fetch_feed(httpx.Client(), api_source)
