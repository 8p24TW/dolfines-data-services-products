from __future__ import annotations

import pandas as pd

from data_sources.base import BaseConnector, normalize_records, utc_now_iso


class ProductHuntStubConnector(BaseConnector):
    name = "product_hunt"
    source_type = "product_hunt"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        return normalize_records([], self.name), {
            "connector": self.name,
            "last_run": utc_now_iso(),
            "status": "stub",
            "record_count": 0,
            "detail": "Stubbed in the MVP because Product Hunt data access is auth-heavy.",
        }


class HuggingFaceStubConnector(BaseConnector):
    name = "hugging_face"
    source_type = "hugging_face"

    def fetch(self) -> tuple[pd.DataFrame, dict]:
        return normalize_records([], self.name), {
            "connector": self.name,
            "last_run": utc_now_iso(),
            "status": "stub",
            "record_count": 0,
            "detail": "Stubbed in the MVP; add a public Hugging Face connector later if needed.",
        }
