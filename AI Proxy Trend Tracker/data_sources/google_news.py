from __future__ import annotations

import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso

_RSS_BASE = "https://news.google.com/rss/search"
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

try:
    import feedparser as _feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False


def _parse_date(raw: str) -> pd.Timestamp:
    try:
        dt = parsedate_to_datetime(raw).astimezone(datetime.timezone.utc)
        return pd.Timestamp(dt)
    except Exception:
        return pd.Timestamp.now(tz="UTC")


def _item_link_xml(item: ET.Element) -> str:
    """Extract link from RSS <item> — handles Google News quirks."""
    link = (item.findtext("link") or "").strip()
    if link.startswith("http"):
        return link
    for child in list(item):
        if child.tag == "link":
            for candidate in [child.tail or "", child.text or ""]:
                candidate = candidate.strip()
                if candidate.startswith("http"):
                    return candidate
    guid = (item.findtext("guid") or "").strip()
    return guid if guid.startswith("http") else ""


def _fetch_with_feedparser(url: str, max_items: int, query: str) -> list[dict]:
    import feedparser  # noqa: PLC0415
    feed = feedparser.parse(url, agent=_BROWSER_UA)
    records = []
    for entry in feed.entries[:max_items]:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        pub = entry.get("published", "") or entry.get("updated", "")
        try:
            dt = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
            date_val = pd.Timestamp(dt)
        except Exception:
            date_val = _parse_date(pub)
        source_name = entry.get("source", {}).get("title", "Google News") if isinstance(entry.get("source"), dict) else "Google News"
        snippet = (entry.get("summary") or "")[:700]
        records.append({
            "source": "google_news",
            "source_type": "google_news",
            "topic": query,
            "title": title,
            "url": link,
            "date": date_val,
            "hits": 1.0,
            "engagement": 0.0,
            "raw_text_snippet": snippet,
            "author": source_name,
            "meta": {"query": query, "news_source": source_name},
        })
    return records


def _fetch_with_xml(resp_content: bytes, max_items: int, query: str) -> list[dict]:
    content = resp_content.lstrip(b"\xef\xbb\xbf").lstrip()
    root = ET.fromstring(content)
    channel = root if root.tag == "channel" else root.find("channel")
    if channel is None:
        raise ValueError("no <channel> element found")
    records = []
    for item in channel.findall("item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = _item_link_xml(item)
        if not title or not link:
            continue
        pub_date = item.findtext("pubDate") or ""
        description = (item.findtext("description") or "")[:700]
        source_el = item.find("source")
        source_name = source_el.text.strip() if source_el is not None and source_el.text else "Google News"
        records.append({
            "source": "google_news",
            "source_type": "google_news",
            "topic": query,
            "title": title,
            "url": link,
            "date": _parse_date(pub_date),
            "hits": 1.0,
            "engagement": 0.0,
            "raw_text_snippet": description,
            "author": source_name,
            "meta": {"query": query, "news_source": source_name},
        })
    return records


class GoogleNewsConnector(BaseConnector):
    name = "google_news"
    source_type = "google_news"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        queries = self.settings.get("google_news_queries", [])
        max_per_query = int(self.settings.get("google_news_max_per_query", 20))
        lang = self.settings.get("google_news_lang", "en-US")
        geo = self.settings.get("google_news_geo", "US")
        ceid = self.settings.get("google_news_ceid", "US:en")

        all_records: list[dict] = []
        seen_urls: set[str] = set()
        errors: list[str] = []

        for query in queries:
            rss_url = (
                f"{_RSS_BASE}?q={quote_plus(query)}"
                f"&hl={lang}&gl={geo}&ceid={ceid}"
            )
            try:
                if _HAS_FEEDPARSER:
                    records = _fetch_with_feedparser(rss_url, max_per_query, query)
                else:
                    resp = self.session.get(
                        rss_url, timeout=20,
                        headers={
                            "User-Agent": _BROWSER_UA,
                            "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
                        },
                    )
                    resp.raise_for_status()
                    records = _fetch_with_xml(resp.content, max_per_query, query)

                for r in records:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_records.append(r)

            except Exception as exc:
                errors.append(f"{query}: {exc}")

        frame = normalize_records(all_records, self.name)
        if errors and frame.empty:
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"Google News failed for all queries. First error: {errors[0]}",
            }
        else:
            detail = f"Fetched {len(frame)} Google News headlines across {len(queries)} queries."
            if errors:
                detail += f" {len(errors)} query/queries failed: {'; '.join(errors[:2])}"
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "ok" if not frame.empty else "warning",
                "record_count": len(frame),
                "detail": detail,
            }
        return frame, status
