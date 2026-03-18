from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class GoogleTrendsConnector(BaseConnector):
    name = "google_trends"
    source_type = "google_trends"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        try:
            from pytrends.request import TrendReq
        except Exception as exc:
            return normalize_records([], self.name), {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"Google Trends connector unavailable because pytrends is missing: {exc}",
            }

        timeframe = self.settings.get("google_trends_timeframe", "today 3-m")
        geo = self.settings.get("google_trends_geo", "")
        keywords = []
        for seed in self.seeds:
            query = seed.get("google_trends_query") or seed.get("topic", "")
            query = query.replace("/", " ").strip()
            if query and query not in keywords:
                keywords.append(query)

        records: list[dict] = []
        try:
            client = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
            for start in range(0, len(keywords), 5):
                batch = keywords[start : start + 5]
                if not batch:
                    continue
                client.build_payload(batch, timeframe=timeframe, geo=geo)
                trend = client.interest_over_time()
                if trend.empty:
                    continue
                if "isPartial" in trend.columns:
                    trend = trend.drop(columns=["isPartial"])
                for keyword in batch:
                    if keyword not in trend.columns:
                        continue
                    series = trend[keyword].dropna()
                    for ts, value in series.items():
                        if float(value) <= 0:
                            continue
                        records.append(
                            {
                                "source": "google_trends",
                                "source_type": self.source_type,
                                "topic": keyword,
                                "title": f"Google search interest for {keyword}",
                                "url": f"https://trends.google.com/trends/explore?date={quote_plus(timeframe)}&q={quote_plus(keyword)}",
                                "date": pd.Timestamp(ts).tz_localize("UTC") if pd.Timestamp(ts).tzinfo is None else pd.Timestamp(ts).tz_convert("UTC"),
                                "hits": float(value) / 10.0,
                                "engagement": float(value),
                                "raw_text_snippet": f"Google Trends relative search interest for {keyword} during {timeframe}.",
                                "author": "google_trends",
                                "meta": {"timeframe": timeframe, "geo": geo, "interest_index": float(value)},
                            }
                        )

            frame = normalize_records(records, self.name)
            status = {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "ok" if not frame.empty else "warning",
                "record_count": len(frame),
                "detail": (
                    f"Fetched Google Trends relative interest over time for {len(keywords)} configured seed topics."
                    if not frame.empty
                    else "Google Trends returned no rows for the configured seed topics."
                ),
            }
            return frame, status
        except Exception as exc:
            return normalize_records([], self.name), {
                "connector": self.name,
                "last_run": utc_now_iso(),
                "status": "error",
                "record_count": 0,
                "detail": f"Google Trends fetch failed: {exc}",
            }
