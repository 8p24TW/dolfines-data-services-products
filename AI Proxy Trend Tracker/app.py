from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from cache.store import CacheStore
from clustering.topics import annotate_mentions
from data_sources.loader import load_settings, load_topic_seeds, refresh_cache
from scoring.advisory_context import enrich_topics_with_8p2_context, load_daily_pulse_signals
from scoring.model import build_topic_snapshot
from ui.components import (
    inject_css,
    render_detail_panel,
    render_header,
    render_bubble_chart,
    render_score_explainer,
    render_summary_cards,
    render_tool_ideas_table,
    render_topic_table,
    style_dark_table,
)


APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = APP_DIR / "config"
CACHE_DB = APP_DIR / "cache" / "ai_proxy_trends.sqlite"
LOGO_PATH = APP_DIR / "8p2 advisory white.png"
DAILY_PULSE_DIR = APP_DIR.parents[1] / "Daily Pulse"


def _load_cache(store: CacheStore) -> tuple[pd.DataFrame, pd.DataFrame]:
    mentions = store.load_mentions()
    statuses = store.load_connector_status()
    return mentions, statuses


def _ensure_data(store: CacheStore) -> tuple[pd.DataFrame, pd.DataFrame]:
    mentions, statuses = _load_cache(store)
    if mentions.empty:
        mentions, statuses = refresh_cache(config_dir=CONFIG_DIR, cache_store=store, include_live=True, include_demo=True)
    return mentions, statuses


def _safe_selection_topic(event) -> str | None:
    try:
        points = event.selection.get("points", []) if event else []
        if points:
            custom_data = points[0].get("customdata", [])
            if custom_data:
                return custom_data[0]
    except Exception:
        return None
    return None


def main() -> None:
    settings = load_settings(CONFIG_DIR)
    seeds = load_topic_seeds(CONFIG_DIR)
    daily_pulse_signals = load_daily_pulse_signals(DAILY_PULSE_DIR)
    st.set_page_config(
        page_title=settings.get("app_title", "AI Proxy Trend Tracker"),
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    store = CacheStore(CACHE_DB)
    mentions_raw, statuses = _ensure_data(store)

    if "selected_topic" not in st.session_state:
        st.session_state.selected_topic = None

    mentions_raw["published_at"] = pd.to_datetime(mentions_raw["published_at"], utc=True, errors="coerce")
    last_refresh = "No refresh yet"
    if not statuses.empty and statuses["last_run"].notna().any():
        last_refresh = pd.to_datetime(statuses["last_run"], utc=True, errors="coerce").max().strftime("%Y-%m-%d %H:%M UTC")

    render_header(settings["app_title"], settings["proxy_notice"], last_refresh, logo_path=LOGO_PATH)

    control_cols = st.columns([1.1, 0.9, 0.9, 0.9, 0.8, 0.7, 0.7])
    time_window = control_cols[0].selectbox("Time window", [1, 7, 14, 30, 90], index=[1, 7, 14, 30, 90].index(settings.get("default_time_window_days", 30)), format_func=lambda v: "24 hours" if v == 1 else f"{v} days")
    view_mode = control_cols[1].selectbox("View mode", ["clustered", "keyword"], format_func=lambda value: "Clustered topics" if value == "clustered" else "Keyword view")
    top_n = control_cols[2].slider("Top topics", min_value=10, max_value=60, value=int(settings.get("default_top_n", 25)), step=5)
    include_live = control_cols[3].checkbox("Use live public sources", value=True)
    include_demo = control_cols[4].checkbox("Include demo fallback", value=True)
    sort_by = control_cols[5].selectbox("Sort by", ["tool_opportunity_score", "growth_7d_pct", "total_hits"], format_func=lambda value: {
        "tool_opportunity_score": "Tool score",
        "growth_7d_pct": "Growth",
        "total_hits": "Hits",
    }[value])
    sort_desc = control_cols[6].checkbox("Desc", value=True)

    action_cols = st.columns([1.1, 0.35, 1.2, 1.2, 1.1])
    search_query = action_cols[0].text_input("Search", placeholder="keyword1, keyword2, ...")
    search_mode = action_cols[1].radio("", ["AND", "OR"], index=0, help="AND = all keywords must appear | OR = any keyword matches")
    available_source_types = sorted(mentions_raw["source_type"].dropna().unique().tolist()) if not mentions_raw.empty else []
    source_filter = action_cols[2].multiselect("Source types", available_source_types, default=available_source_types)
    mentions_annotated = annotate_mentions(mentions_raw, seeds, settings) if not mentions_raw.empty else pd.DataFrame()
    available_categories = sorted(mentions_annotated["category"].dropna().unique().tolist()) if not mentions_annotated.empty else []
    category_filter = action_cols[3].multiselect("Categories", available_categories, default=available_categories)
    if action_cols[4].button("Refresh data", use_container_width=True, type="primary"):
        with st.spinner("Refreshing public/proxy data..."):
            mentions_raw, statuses = refresh_cache(
                config_dir=CONFIG_DIR,
                cache_store=store,
                include_live=include_live,
                include_demo=include_demo,
            )
            mentions_annotated = annotate_mentions(mentions_raw, seeds, settings) if not mentions_raw.empty else pd.DataFrame()
            st.session_state.selected_topic = None

    if mentions_annotated.empty:
        st.warning("No data is available yet. Refresh the sources or enable the demo fallback.")
        return

    google_status = ""
    if not statuses.empty and "connector" in statuses.columns:
        google_rows = statuses.loc[statuses["connector"] == "google_trends"]
        if not google_rows.empty:
            google_row = google_rows.iloc[-1]
            google_status = f"Google Trends: {google_row['status']}."
    st.caption(
        f"Current live-source mix combines Reddit, Hacker News, GitHub Trending, Google Trends, and Google News when available. "
        f"{google_status} This remains a public/proxy-signal dashboard."
    )

    as_of = mentions_annotated["published_at"].max()
    cutoff = as_of - pd.Timedelta(hours=time_window * 24)
    filtered = mentions_annotated.loc[mentions_annotated["published_at"] >= cutoff].copy()
    if source_filter:
        filtered = filtered.loc[filtered["source_type"].isin(source_filter)]
    if category_filter:
        filtered = filtered.loc[filtered["category"].isin(category_filter)]
    if search_query.strip():
        import re as _re
        terms = [t.strip().lower() for t in search_query.split(",") if t.strip()]
        patterns = [_re.compile(r'\b' + _re.escape(t) + r'\b') for t in terms]
        mask = filtered["search_blob"].str.lower().fillna("")
        combiner = all if search_mode == "AND" else any
        filtered = filtered.loc[mask.apply(lambda s: combiner(p.search(s) for p in patterns))]

    topics = build_topic_snapshot(filtered, settings=settings, view_mode=view_mode, top_n=top_n)
    if topics.empty:
        st.info("No topics matched the selected filters. Broaden the time window or source/category filters.")
        return
    topics = enrich_topics_with_8p2_context(topics, daily_pulse_signals)

    topics = topics.sort_values(sort_by, ascending=not sort_desc).reset_index(drop=True)
    selected_topic = st.session_state.selected_topic or topics.iloc[0]["topic"]
    if selected_topic not in topics["topic"].tolist():
        selected_topic = topics.iloc[0]["topic"]
    st.session_state.selected_topic = selected_topic

    fastest = topics.sort_values("growth_7d_pct", ascending=False).iloc[0]
    highest_hits = topics.sort_values("total_hits", ascending=False).iloc[0]
    top_tool = topics.sort_values("tool_opportunity_score", ascending=False).iloc[0]
    summary_cards = [
        {"label": "Topics tracked", "value": f"{len(topics):,}", "meta": f"{time_window}-day filtered view"},
        {"label": "Fastest growing", "value": fastest["topic"], "meta": f"{fastest['growth_7d_pct']:.1f}% 7d growth"},
        {"label": "Highest volume", "value": highest_hits["topic"], "meta": f"{highest_hits['total_hits']:.1f} proxy hits"},
        {"label": "Top tool opportunity", "value": top_tool["topic"], "meta": f"Score {top_tool['tool_opportunity_score']:.0f}/100"},
    ]
    render_summary_cards(summary_cards)

    st.markdown("### Bubble chart")
    st.caption("Bubble size = proxy hit score | Color = momentum status | X = 7-day growth | Y = AI tool opportunity / relevance")
    render_bubble_chart(topics, selected_topic=st.session_state.selected_topic, height=660)

    st.markdown("### Topic table")
    csv_payload = topics[
        ["topic", "total_hits", "growth_7d_pct", "trend_30d_pct", "source_breakdown", "category", "tool_opportunity_score", "last_updated", "status_flag"]
    ].to_csv(index=False)
    st.download_button("Export CSV", csv_payload, file_name="ai_proxy_topic_snapshot.csv", mime="text/csv", use_container_width=True)
    table_selected = render_topic_table(topics, st.session_state.selected_topic)
    if table_selected:
        st.session_state.selected_topic = table_selected

    selected_topic = st.session_state.selected_topic
    selected_row = topics.loc[topics["topic"] == selected_topic].iloc[0]
    detail_col_name = "cluster_topic" if view_mode == "clustered" else "keyword_label"
    detail_mentions = filtered.loc[filtered[detail_col_name] == selected_topic].copy()

    st.markdown("### Tool opportunity table")
    render_tool_ideas_table(topics)

    st.markdown("### Topic detail")
    detail_col, score_col = st.columns([1.3, 1.0], gap="large")
    with detail_col:
        render_detail_panel(selected_row, detail_mentions)
    with score_col:
        render_score_explainer(selected_row)

    with st.expander("Connector status and source coverage", expanded=False):
        if statuses.empty:
            st.caption("No connector status is available yet.")
        else:
            status_display = statuses.copy()
            status_display["last_run"] = pd.to_datetime(status_display["last_run"], utc=True, errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(style_dark_table(status_display), use_container_width=True, hide_index=True)
        st.caption(
            "Implemented live connectors in the MVP: Reddit posts, Hacker News public search, GitHub Trending, and Google Trends. "
            "Hugging Face and Product Hunt remain stubs."
        )


if __name__ == "__main__":
    main()
