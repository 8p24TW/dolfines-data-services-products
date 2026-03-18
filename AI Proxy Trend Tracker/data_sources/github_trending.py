from __future__ import annotations

import html
import re

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class GitHubTrendingConnector(BaseConnector):
    name = "github"
    source_type = "github"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        ai_keywords = tuple(self.settings.get("ai_keywords", []))
        records: list[dict] = []
        try:
            resp = self.session.get("https://github.com/trending?since=daily", timeout=20)
            resp.raise_for_status()
            articles = re.findall(r"<article[^>]*Box-row[^>]*>(.*?)</article>", resp.text, flags=re.IGNORECASE | re.DOTALL)
            for article in articles:
                link_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', article, flags=re.IGNORECASE | re.DOTALL)
                if not link_match:
                    continue
                repo_href = link_match.group(1)
                repo_name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", link_match.group(2)))).strip()
                desc_match = re.search(r"<p[^>]*>(.*?)</p>", article, flags=re.IGNORECASE | re.DOTALL)
                description_text = ""
                if desc_match:
                    description_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", desc_match.group(1)))).strip()
                haystack = f"{repo_name} {description_text}".lower()
                if ai_keywords and not any(term in haystack for term in ai_keywords):
                    continue
                stars_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", article))).strip()
                today_match = re.search(r"([\d,]+)\s+stars\s+today", stars_text, flags=re.IGNORECASE)
                today_stars = int(today_match.group(1).replace(",", "")) if today_match else 0
                records.append(
                    {
                        "source": "github_trending",
                        "source_type": self.source_type,
                        "topic": "",
                        "title": repo_name,
                        "url": f"https://github.com{repo_href}",
                        "date": utc_now_iso(),
                        "hits": 1,
                        "engagement": float(today_stars),
                        "raw_text_snippet": description_text,
                        "author": "",
                        "meta": {"stars_today": today_stars},
                    }
                )
            frame = normalize_records(records, self.name)
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "ok",
                "record_count": len(frame),
                "detail": "Scraped GitHub Trending and retained AI-related repositories by keyword filter.",
            }
            return frame, status
        except Exception as exc:
            return normalize_records([], self.name), {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"GitHub Trending fetch failed: {exc}",
            }
