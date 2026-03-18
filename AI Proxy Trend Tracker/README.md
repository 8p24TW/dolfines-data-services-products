# AI Proxy Trend Tracker

Local MVP for finding trending and emerging AI topics from **public / proxy trend signals — not direct ChatGPT or Claude keyword data**.

## What the MVP does

- Pulls public signals from Reddit posts, Hacker News public search, and GitHub Trending
- Pulls Google Trends relative search-interest data for the seeded topic list
- Falls back to deterministic seeded demo data when live loading is unavailable
- Normalizes mentions into topic families or keyword view
- Scores each topic for volume, momentum, source diversity, commercial intent, and AI tool opportunity
- Shows a Streamlit dashboard with:
  - summary cards
  - bubble chart
  - sortable/filterable topic table
  - selected-topic detail panel
  - CSV export
  - manual refresh

## Project structure

- `app.py`: Streamlit dashboard
- `refresh_data.py`: manual/daily refresh script
- `data_sources/`: source connectors and loader
- `clustering/`: topic extraction and normalization
- `scoring/`: trend and opportunity scoring
- `ui/`: dashboard components
- `config/`: editable topic seeds and settings
- `cache/`: SQLite cache

## Setup

```bash
cd "dolfines-data-services-products/AI Proxy Trend Tracker"
pip install -r requirements.txt
python refresh_data.py --demo-only
streamlit run app.py
```

Use `python refresh_data.py` for live public sources plus demo fallback, or `python refresh_data.py --live-only` to skip demo data.

## Implemented vs stubbed sources

Implemented in MVP:

- Reddit public subreddit posts via JSON endpoints
- Hacker News via the public Algolia API
- GitHub Trending via lightweight HTML scraping
- Google Trends via `pytrends` relative interest-over-time queries
- Seeded demo signal generator for offline use

Stubbed for later:

- Product Hunt
- Hugging Face trending
- Newsletter / RSS connectors
- Reddit comments

The stubs are explicit in the UI so the app remains honest about current coverage.
Google Trends is an unofficial/public connector, so it may be rate-limited or temporarily unavailable depending on the upstream service.

## Scoring model

The scoring is heuristic and intentionally transparent.

### 1. Total hit score

Each mention gets a weighted hit value:

- `weighted_hits = hits * source_weight * (1 + log1p(engagement) / 8)`

`source_weight` is configurable in `config/settings.json`.

### 2. Growth

- `7d growth % = ((recent_7d_hits + 1) / (prior_7d_hits + 1) - 1) * 100`
- `30d trend % = ((recent_30d_hits + 1) / (prior_30d_hits + 1) - 1) * 100`

This avoids divide-by-zero explosions while still surfacing genuinely new topics.

### 3. Source diversity score

- Based on the number of distinct source families mentioning a topic
- Scaled to a 0-100 score

### 4. Commercial intent score

- Based on configurable commercial keywords such as `workflow`, `reporting`, `compliance`, `proposal`, `dashboard`, and `api`
- Seed-topic commercial cues add to the score

### 5. AI tool opportunity score

Main MVP formula:

- `35% growth score`
- `20% volume score`
- `20% source diversity score`
- `25% commercial intent score`
- `+10 new-topic bonus` if first seen within 14 days

This is implemented in `scoring/model.py`.

### Interpreting the score

- A topic can score highly from fast acceleration even if absolute volume is still moderate
- A topic with large hit volume but weak growth may still rank well, but usually below sharper emerging topics
- Source diversity matters because single-source spikes are less reliable
- Commercial intent matters because the app is trying to surface potential product/tool opportunities, not just general buzz
- The selected-topic panel in the app shows the exact component breakdown for each topic
- The main topic table now shows a score plus a one-month inline trend chart rather than multiple progress columns

## Topic extraction / clustering

The MVP uses a practical rule-based approach:

- lowercase and clean text
- remove stopwords
- match against editable seed families in `config/topic_seeds.json`
- if no seed match exists, extract a fallback keyword phrase from the mention text

This keeps the MVP easy to inspect and modify. Embeddings/fuzzy matching can be added later if needed.

## Notes

- This is a **proxy-signal dashboard**, not direct user-query telemetry.
- Live source access depends on local network access and the upstream sites remaining publicly reachable.
- If live fetches fail, the demo generator keeps the app usable for UI testing and heuristic tuning.
