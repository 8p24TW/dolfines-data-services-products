from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cache.store import CacheStore
from data_sources.demo_source import DemoConnector
from data_sources.google_news import GoogleNewsConnector
from data_sources.google_trends import GoogleTrendsConnector
from data_sources.github_trending import GitHubTrendingConnector
from data_sources.hacker_news import HackerNewsConnector
from data_sources.reddit import RedditConnector
from data_sources.stubs import HuggingFaceStubConnector, ProductHuntStubConnector


def load_json(path: Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_settings(config_dir: Path) -> dict:
    return load_json(Path(config_dir) / "settings.json")


def load_topic_seeds(config_dir: Path) -> list[dict]:
    return load_json(Path(config_dir) / "topic_seeds.json")


def build_connectors(settings: dict, seeds: list[dict], include_live: bool, include_demo: bool):
    connectors = []
    if include_live:
        connectors.extend(
            [
                RedditConnector(settings, seeds),
                HackerNewsConnector(settings, seeds),
                GitHubTrendingConnector(settings, seeds),
                GoogleTrendsConnector(settings, seeds),
                GoogleNewsConnector(settings, seeds),
                ProductHuntStubConnector(settings, seeds),
                HuggingFaceStubConnector(settings, seeds),
            ]
        )
    if include_demo:
        connectors.append(DemoConnector(settings, seeds))
    return connectors


def refresh_cache(
    *,
    config_dir: Path,
    cache_store: CacheStore,
    include_live: bool = True,
    include_demo: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    settings = load_settings(config_dir)
    seeds = load_topic_seeds(config_dir)
    connectors = build_connectors(settings, seeds, include_live=include_live, include_demo=include_demo)
    mention_frames = []
    statuses = []
    for connector in connectors:
        frame, status = connector.fetch()
        if not frame.empty:
            mention_frames.append(frame)
        statuses.append(status)
    if not mention_frames and not include_demo:
        demo_frame, demo_status = DemoConnector(settings, seeds).fetch()
        mention_frames.append(demo_frame)
        demo_status["detail"] = f"{demo_status['detail']} Fallback activated because all live sources returned zero rows."
        statuses.append(demo_status)
    mentions = pd.concat(mention_frames, ignore_index=True) if mention_frames else pd.DataFrame()
    mentions = mentions.drop_duplicates(subset=["record_id"]) if not mentions.empty else mentions
    status_df = pd.DataFrame(statuses)
    cache_store.save_mentions(mentions)
    cache_store.save_connector_status(status_df)
    return mentions, status_df
