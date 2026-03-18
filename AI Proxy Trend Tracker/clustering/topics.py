from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for", "from", "how",
    "in", "into", "is", "it", "its", "more", "new", "of", "on", "or", "that", "the", "their",
    "this", "to", "up", "using", "with", "what", "where", "when", "why", "your", "you", "vs",
    "after", "before", "than", "out", "about", "over", "under", "via", "top", "best", "show",
    "shows", "showing", "discussion", "builder", "builders", "product", "products", "tool",
    "tools", "software", "launch", "launches", "around", "focuses", "focused", "possible"
}


def normalize_text(text: str) -> str:
    clean = (text or "").lower()
    clean = re.sub(r"http\S+", " ", clean)
    clean = re.sub(r"[^a-z0-9+\-/&\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def tokenize(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if len(token) > 2 and token not in STOPWORDS]


def match_seed_topic(text: str, seeds: list[dict]) -> tuple[dict | None, str, int]:
    best_seed = None
    best_alias = ""
    best_score = 0
    for seed in seeds:
        score = 0
        alias_match = ""
        for alias in seed.get("aliases", []):
            alias_clean = normalize_text(alias)
            if alias_clean and alias_clean in text:
                alias_score = len(alias_clean.split()) + 1
                if alias_score > score:
                    alias_match = alias
                score += alias_score
        if score > best_score:
            best_seed = seed
            best_alias = alias_match or seed["topic"]
            best_score = score
    return best_seed, best_alias, best_score


def extract_keyphrase(text: str) -> str:
    tokens = tokenize(text)
    if not tokens:
        return "Other AI topic"
    if len(tokens) == 1:
        return tokens[0].title()
    ngrams = []
    for size in (3, 2):
        for idx in range(0, max(len(tokens) - size + 1, 0)):
            gram_tokens = tokens[idx : idx + size]
            if any(token in {"ai", "llm", "agent", "automation", "copilot", "rag"} for token in gram_tokens):
                ngrams.append(" ".join(gram_tokens))
    if ngrams:
        return Counter(ngrams).most_common(1)[0][0].title()
    return " ".join(tokens[:2]).title()


def annotate_mentions(raw_mentions: pd.DataFrame, seeds: list[dict], settings: dict) -> pd.DataFrame:
    if raw_mentions.empty:
        return raw_mentions.copy()
    mentions = raw_mentions.copy()
    mentions["published_at"] = pd.to_datetime(mentions["published_at"], utc=True, errors="coerce")
    mentions = mentions.dropna(subset=["published_at"]).reset_index(drop=True)
    source_weights = settings.get("source_weights", {})
    commercial_keywords = [normalize_text(item) for item in settings.get("commercial_intent_keywords", [])]

    cluster_topics = []
    keyword_labels = []
    categories = []
    tool_ideas = []
    commercial_scores = []
    cleaned_texts = []

    for row in mentions.itertuples(index=False):
        body_text = " ".join([str(getattr(row, "title", "") or ""), str(getattr(row, "snippet", "") or ""), str(getattr(row, "topic_hint", "") or "")])
        cleaned = normalize_text(body_text)
        seed, alias, _ = match_seed_topic(cleaned, seeds)
        fallback_phrase = extract_keyphrase(cleaned)
        cluster_topic = seed["topic"] if seed else fallback_phrase
        keyword_label = alias.title() if alias else fallback_phrase
        category = seed.get("category", "Emerging / Other") if seed else "Emerging / Other"
        tool_idea = (
            seed.get("tool_idea")
            if seed
            else f"Possible AI workflow or monitoring product around {fallback_phrase.lower()}."
        )
        cue_hits = sum(1 for cue in commercial_keywords if cue and cue in cleaned)
        if seed:
            cue_hits += sum(1 for cue in seed.get("commercial_cues", []) if normalize_text(cue) in cleaned)
        commercial_score = min(1.0, 0.16 * cue_hits + 0.05 * (getattr(row, "engagement", 0.0) > 25))

        cluster_topics.append(cluster_topic)
        keyword_labels.append(keyword_label)
        categories.append(category)
        tool_ideas.append(tool_idea)
        commercial_scores.append(commercial_score)
        cleaned_texts.append(cleaned)

    mentions["cluster_topic"] = cluster_topics
    mentions["keyword_label"] = keyword_labels
    mentions["category"] = categories
    mentions["tool_idea_seed"] = tool_ideas
    mentions["commercial_intent_raw"] = commercial_scores
    mentions["clean_text"] = cleaned_texts
    mentions["mention_date"] = mentions["published_at"].dt.floor("D")
    mentions["source_weight"] = mentions["source_type"].map(source_weights).fillna(1.0)
    mentions["engagement"] = mentions["engagement"].fillna(0.0).astype(float)
    mentions["hits"] = mentions["hits"].fillna(1.0).astype(float)
    mentions["weighted_hits"] = mentions["hits"] * mentions["source_weight"] * (1.0 + np.log1p(mentions["engagement"].clip(lower=0.0)) / 8.0)
    mentions["search_blob"] = (
        mentions["cluster_topic"].fillna("")
        + " "
        + mentions["keyword_label"].fillna("")
        + " "
        + mentions["title"].fillna("")
        + " "
        + mentions["snippet"].fillna("")
    ).str.lower()
    return mentions
