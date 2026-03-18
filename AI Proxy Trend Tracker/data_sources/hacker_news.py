from __future__ import annotations

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class HackerNewsConnector(BaseConnector):
    name = "hacker_news"
    source_type = "hacker_news"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        queries = self.settings.get("hacker_news_queries", [])
        max_records = int(self.settings.get("max_records_per_source", 60))
        records: list[dict] = []
        seen_urls: set[str] = set()
        try:
            for query in queries:
                resp = self.session.get(
                    "https://hn.algolia.com/api/v1/search_by_date",
                    params={"query": query, "tags": "story", "hitsPerPage": min(max_records, 40)},
                    timeout=20,
                )
                resp.raise_for_status()
                for item in resp.json().get("hits", []):
                    title = (item.get("title") or item.get("story_title") or "").strip()
                    url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}"
                    if not title or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    records.append(
                        {
                            "source": "hacker_news",
                            "source_type": self.source_type,
                            "topic": query,
                            "title": title,
                            "url": url,
                            "date": item.get("created_at"),
                            "hits": 1,
                            "engagement": float(item.get("points", 0) or 0) + (float(item.get("num_comments", 0) or 0) * 2),
                            "raw_text_snippet": item.get("story_text") or "",
                            "author": item.get("author", ""),
                            "meta": {"query": query},
                        }
                    )
            frame = normalize_records(records, self.name)
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "ok",
                "record_count": len(frame),
                "detail": f"Fetched public Algolia Hacker News results for {len(queries)} AI umbrella queries.",
            }
            return frame, status
        except Exception as exc:
            return normalize_records([], self.name), {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"Hacker News fetch failed: {exc}",
            }
