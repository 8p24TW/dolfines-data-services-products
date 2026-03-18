from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import pandas as pd
import requests


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_record_id(source: str, url: str, title: str, published_at: str) -> str:
    payload = f"{source}|{url}|{title}|{published_at}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def normalize_records(records: list[dict], connector_name: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "record_id",
                "source",
                "source_type",
                "title",
                "url",
                "published_at",
                "hits",
                "engagement",
                "snippet",
                "topic_hint",
                "author",
                "meta_json",
                "connector",
            ]
        )
    rows = []
    for record in records:
        published_at = pd.to_datetime(record.get("date"), utc=True, errors="coerce")
        published_iso = published_at.isoformat() if pd.notna(published_at) else utc_now_iso()
        source = record.get("source", connector_name)
        title = (record.get("title") or "").strip()
        url = record.get("url") or ""
        rows.append(
            {
                "record_id": make_record_id(source, url, title, published_iso),
                "source": source,
                "source_type": record.get("source_type", connector_name),
                "title": title,
                "url": url,
                "published_at": published_iso,
                "hits": float(record.get("hits", 1.0) or 1.0),
                "engagement": float(record.get("engagement", 0.0) or 0.0),
                "snippet": (record.get("raw_text_snippet") or record.get("snippet") or "")[:700],
                "topic_hint": record.get("topic") or record.get("keyword") or "",
                "author": record.get("author") or "",
                "meta_json": json.dumps(record.get("meta", {}), ensure_ascii=True),
                "connector": connector_name,
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["record_id"])


class BaseConnector(ABC):
    name = "base"
    source_type = "base"

    def __init__(self, settings: dict, seeds: list[dict]) -> None:
        self.settings = settings
        self.seeds = seeds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "AIProxyTrendTracker/0.1 (+public-proxy-signals local MVP)",
                "Accept": "application/json,text/html,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    @abstractmethod
    def fetch(self) -> tuple[pd.DataFrame, dict]:
        raise NotImplementedError
