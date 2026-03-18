from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from clustering.topics import tokenize


def _growth_pct(recent_hits: float, prior_hits: float, cap_pct: float) -> float:
    growth = ((recent_hits + 1.0) / (prior_hits + 1.0) - 1.0) * 100.0
    return float(np.clip(growth, -100.0, cap_pct))


def _sparkline(values: list[float]) -> str:
    ticks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    max_value = max(values)
    if max_value <= 0:
        return ticks[0] * len(values)
    return "".join(ticks[min(len(ticks) - 1, int((value / max_value) * (len(ticks) - 1)))] for value in values)


def _status_flag(first_seen: pd.Timestamp, growth_7d_pct: float, recent_7_hits: float, as_of: pd.Timestamp) -> str:
    if pd.notna(first_seen) and (as_of - first_seen).days <= 7 and recent_7_hits >= 3:
        return "new"
    if growth_7d_pct >= 25:
        return "rising"
    if growth_7d_pct <= -15:
        return "falling"
    return "stable"


def _summarize_topic(topic: str, category: str, source_breakdown: dict[str, int], headlines: list[str], growth_7d_pct: float) -> str:
    sources = ", ".join(f"{key} ({value})" for key, value in list(source_breakdown.items())[:3])
    tokens = Counter(token for title in headlines[:5] for token in tokenize(title))
    top_terms = ", ".join(token for token, _ in tokens.most_common(3))
    momentum = "accelerating" if growth_7d_pct >= 25 else "steady" if growth_7d_pct >= -15 else "cooling"
    if not top_terms:
        top_terms = "operator workflows"
    return f"{topic} is {momentum} across {sources or 'limited sources'}, with discussion centering on {top_terms} in {category.lower()} use cases."


def _tool_idea(topic: str, seed_tool_idea: str, commercial_intent_score: float, dominant_source: str) -> str:
    if seed_tool_idea:
        return seed_tool_idea
    suffix = "monitoring tool" if "github" in dominant_source else "workflow product"
    qualifier = "strong" if commercial_intent_score >= 65 else "emerging"
    return f"Possible {qualifier} AI {suffix} around {topic.lower()}."


def _risk_notes(source_diversity_count: int, dominant_source_share: float, used_demo: bool) -> str:
    notes = []
    if source_diversity_count <= 1:
        notes.append("signal is concentrated in one source family")
    if dominant_source_share >= 0.75:
        notes.append("topic is dominated by one source")
    if used_demo:
        notes.append("includes demo data for offline continuity")
    return "; ".join(notes) if notes else "proxy signals look reasonably diversified"


def build_topic_snapshot(
    mentions: pd.DataFrame,
    *,
    settings: dict,
    view_mode: str = "clustered",
    top_n: int = 25,
) -> pd.DataFrame:
    if mentions.empty:
        return pd.DataFrame()

    topic_col = "cluster_topic" if view_mode == "clustered" else "keyword_label"
    cap_pct = float(settings.get("growth_cap_pct", 300))
    as_of = mentions["published_at"].max().floor("D")
    rows = []

    for topic, group in mentions.groupby(topic_col):
        if not str(topic).strip():
            continue
        group = group.sort_values("published_at")
        recent_7 = group.loc[group["published_at"] >= (as_of - pd.Timedelta(days=6)), "weighted_hits"].sum()
        prior_7 = group.loc[
            (group["published_at"] >= (as_of - pd.Timedelta(days=13))) & (group["published_at"] < (as_of - pd.Timedelta(days=6))),
            "weighted_hits",
        ].sum()
        recent_30 = group.loc[group["published_at"] >= (as_of - pd.Timedelta(days=29)), "weighted_hits"].sum()
        prior_30 = group.loc[
            (group["published_at"] >= (as_of - pd.Timedelta(days=59))) & (group["published_at"] < (as_of - pd.Timedelta(days=29))),
            "weighted_hits",
        ].sum()
        growth_7d_pct = _growth_pct(recent_7, prior_7, cap_pct)
        trend_30_pct = _growth_pct(recent_30, prior_30, cap_pct)
        source_counts = group["source_type"].value_counts().to_dict()
        source_diversity_count = int(group["source_type"].nunique())
        source_diversity_score = min(100.0, (source_diversity_count / 4.0) * 100.0)
        commercial_intent_score = float(group["commercial_intent_raw"].mean() * 100.0)
        total_hits = float(group["weighted_hits"].sum())
        mention_count = int(len(group))
        daily_hits = (
            group.groupby("mention_date")["weighted_hits"].sum().reindex(pd.date_range(as_of - pd.Timedelta(days=13), as_of, freq="D"), fill_value=0.0)
        )
        monthly_hits = (
            group.groupby("mention_date")["weighted_hits"].sum().reindex(pd.date_range(as_of - pd.Timedelta(days=29), as_of, freq="D"), fill_value=0.0)
        )
        dominant_source = max(source_counts, key=source_counts.get) if source_counts else "unknown"
        dominant_source_share = (max(source_counts.values()) / sum(source_counts.values())) if source_counts else 1.0
        first_seen = group["published_at"].min()
        last_seen = group["published_at"].max()
        status_flag = _status_flag(first_seen, growth_7d_pct, recent_7, as_of)
        used_demo = bool((group["source_type"] == "demo").any())
        seed_tool_idea = group["tool_idea_seed"].mode().iloc[0] if group["tool_idea_seed"].notna().any() else ""
        summary = _summarize_topic(topic, group["category"].mode().iloc[0], source_counts, group["title"].tolist(), growth_7d_pct)
        rows.append(
            {
                "topic": topic,
                "category": group["category"].mode().iloc[0],
                "total_hits": total_hits,
                "mention_count": mention_count,
                "growth_7d_pct": growth_7d_pct,
                "trend_30d_pct": trend_30_pct,
                "source_diversity_score": source_diversity_score,
                "source_diversity_count": source_diversity_count,
                "commercial_intent_score": commercial_intent_score,
                "status_flag": status_flag,
                "source_breakdown": " | ".join(f"{source}: {count}" for source, count in source_counts.items()),
                "dominant_source": dominant_source,
                "first_seen": first_seen,
                "last_updated": last_seen,
                "summary": summary,
                "tool_idea": _tool_idea(topic, seed_tool_idea, commercial_intent_score, dominant_source),
                "risk_notes": _risk_notes(source_diversity_count, dominant_source_share, used_demo),
                "sparkline_14d": _sparkline(daily_hits.tolist()),
                "sparkline_30d": _sparkline(monthly_hits.tolist()),
                "trend_series_30d": [float(value) for value in monthly_hits.tolist()],
            }
        )

    topics = pd.DataFrame(rows)
    if topics.empty:
        return topics

    topics["volume_score"] = topics["total_hits"].rank(pct=True).mul(100.0)
    topics["growth_score"] = (((topics["growth_7d_pct"].clip(-100.0, cap_pct) + 100.0) / (cap_pct + 100.0)) * 100.0).clip(0.0, 100.0)
    topics["new_topic_bonus"] = np.where((as_of - topics["first_seen"]).dt.days <= 14, 10.0, 0.0)
    # MVP heuristic:
    # tool_opportunity = 35% growth + 20% volume + 20% source diversity + 25% commercial intent + small new-topic bonus
    topics["tool_opportunity_score"] = (
        0.35 * topics["growth_score"]
        + 0.20 * topics["volume_score"]
        + 0.20 * topics["source_diversity_score"]
        + 0.25 * topics["commercial_intent_score"]
        + topics["new_topic_bonus"]
    ).clip(0.0, 100.0)
    topics["score_growth_component"] = 0.35 * topics["growth_score"]
    topics["score_volume_component"] = 0.20 * topics["volume_score"]
    topics["score_diversity_component"] = 0.20 * topics["source_diversity_score"]
    topics["score_commercial_component"] = 0.25 * topics["commercial_intent_score"]
    # Relevance axis blends tool potential and commercial intent so the Y-axis remains decision-oriented.
    topics["relevance_score"] = (0.60 * topics["tool_opportunity_score"] + 0.40 * topics["commercial_intent_score"]).clip(0.0, 100.0)
    topics = topics.sort_values(["tool_opportunity_score", "total_hits"], ascending=[False, False]).head(top_n).reset_index(drop=True)
    return topics
