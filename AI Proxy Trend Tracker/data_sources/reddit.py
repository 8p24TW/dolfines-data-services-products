from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class RedditConnector(BaseConnector):
    name = "reddit"
    source_type = "reddit"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        records: list[dict] = []
        max_records = int(self.settings.get("max_records_per_source", 60))
        subreddits = self.settings.get("reddit_subreddits", [])
        ai_keywords = tuple(self.settings.get("ai_keywords", []))
        try:
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={min(max_records, 40)}"
                resp = self.session.get(url, timeout=20)
                resp.raise_for_status()
                payload = resp.json()
                for child in payload.get("data", {}).get("children", []):
                    data = child.get("data", {})
                    title = (data.get("title") or "").strip()
                    snippet = (data.get("selftext") or "")[:500]
                    if subreddit.lower() in {"entrepreneur", "saas"}:
                        haystack = f"{title} {snippet}".lower()
                        if ai_keywords and not any(term in haystack for term in ai_keywords):
                            continue
                    created = datetime.fromtimestamp(float(data.get("created_utc", 0)), tz=UTC)
                    records.append(
                        {
                            "source": f"reddit:r/{subreddit}",
                            "source_type": self.source_type,
                            "topic": "",
                            "title": title,
                            "url": f"https://www.reddit.com{data.get('permalink', '')}",
                            "date": created.isoformat(),
                            "hits": 1,
                            "engagement": float(data.get("ups", 0) or 0) + (float(data.get("num_comments", 0) or 0) * 1.5),
                            "raw_text_snippet": snippet,
                            "author": data.get("author", ""),
                            "meta": {"num_comments": data.get("num_comments", 0)},
                        }
                    )
            frame = normalize_records(records, self.name)
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "ok",
                "record_count": len(frame),
                "detail": f"Fetched public subreddit posts from {len(subreddits)} subreddits.",
            }
            return frame, status
        except Exception as exc:
            return normalize_records([], self.name), {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"Reddit fetch failed: {exc}",
            }
