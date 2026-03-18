from __future__ import annotations

import argparse
from pathlib import Path

from cache.store import CacheStore
from data_sources.loader import refresh_cache


APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = APP_DIR / "config"
CACHE_DB = APP_DIR / "cache" / "ai_proxy_trends.sqlite"


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh cached public/proxy AI trend data.")
    parser.add_argument("--demo-only", action="store_true", help="Use only the seeded demo connector.")
    parser.add_argument("--live-only", action="store_true", help="Use only live public-source connectors.")
    args = parser.parse_args()

    include_live = not args.demo_only
    include_demo = not args.live_only
    store = CacheStore(CACHE_DB)
    mentions, statuses = refresh_cache(
        config_dir=CONFIG_DIR,
        cache_store=store,
        include_live=include_live,
        include_demo=include_demo,
    )
    print(f"Cached {len(mentions):,} mention records to {CACHE_DB}")
    if not statuses.empty:
        for row in statuses.itertuples(index=False):
            print(f"{row.connector}: {row.status} ({row.record_count}) - {row.detail}")


if __name__ == "__main__":
    main()
