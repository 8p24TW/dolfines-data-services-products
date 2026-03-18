from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class DemoConnector(BaseConnector):
    name = "demo"
    source_type = "demo"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        rng = random.Random(42)
        now = datetime.now(UTC)
        records: list[dict] = []
        source_map = [
            ("reddit:r/ChatGPT", "reddit"),
            ("reddit:r/LocalLLaMA", "reddit"),
            ("reddit:r/SaaS", "reddit"),
            ("hacker_news", "hacker_news"),
            ("github_trending", "github"),
            ("newsletter:rss", "newsletter"),
        ]
        growth_profiles = {
            "AI agents": (1.8, 4.2),
            "Workflow automation": (1.3, 2.7),
            "AI note taking": (1.2, 1.4),
            "AI coding tools": (2.0, 2.3),
            "Legal AI": (0.8, 1.9),
            "Finance AI": (0.9, 1.8),
            "Recruiting AI": (0.8, 1.5),
            "Solar AI": (0.6, 1.0),
            "Wind AI": (0.6, 1.1),
            "BESS AI": (0.5, 1.7),
            "Project management AI": (0.8, 1.4),
            "Due diligence AI": (0.7, 1.9),
            "Reporting automation": (1.1, 2.4),
            "RFP / tender AI": (0.5, 1.6),
            "Knowledge management AI": (1.0, 2.0),
            "RAG systems": (1.4, 1.8),
        }

        for seed in self.seeds:
            topic = seed["topic"]
            aliases = seed.get("aliases", [topic])
            baseline, recent_boost = growth_profiles.get(topic, (0.6, 1.1))
            for days_ago in range(0, 45):
                day = now - timedelta(days=days_ago)
                weekend_factor = 0.78 if day.weekday() >= 5 else 1.0
                momentum = recent_boost if days_ago <= 7 else baseline
                mentions = max(0, int(round(rng.uniform(0.0, 1.3) * momentum * weekend_factor)))
                for idx in range(mentions):
                    alias = rng.choice(aliases)
                    source, source_type = rng.choice(source_map)
                    commercial_suffix = rng.choice(
                        [
                            "for enterprise workflows",
                            "for reporting teams",
                            "for ops leaders",
                            "for SaaS builders",
                            "for technical diligence",
                            "for energy operations",
                        ]
                    )
                    title = rng.choice(
                        [
                            f"{alias.title()} is showing up in more product discussions {commercial_suffix}",
                            f"Builders are exploring {alias} {commercial_suffix}",
                            f"New launch around {alias} focuses on automation {commercial_suffix}",
                            f"Operators discuss where {alias} creates measurable ROI",
                        ]
                    )
                    snippet = (
                        f"Proxy demo signal for {topic}. Discussion references {alias}, "
                        f"{seed.get('category', 'AI')} use cases, and likely product demand."
                    )
                    records.append(
                        {
                            "source": source,
                            "source_type": source_type,
                            "topic": alias,
                            "title": title,
                            "url": f"https://example.com/{topic.lower().replace(' ', '-')}/{days_ago}/{idx}",
                            "date": (day - timedelta(hours=rng.randint(0, 20))).isoformat(),
                            "hits": 1,
                            "engagement": rng.randint(3, 120),
                            "raw_text_snippet": snippet,
                            "author": "demo",
                            "meta": {"demo": True, "generated_at": utc_now_iso()},
                        }
                    )
        frame = normalize_records(records, self.name)
        status = {
            "connector": self.name,
            "last_run": utc_now_iso(),
            "status": "ok",
            "record_count": len(frame),
            "detail": "Generated deterministic seeded proxy records for offline/demo mode.",
        }
        return frame, status
