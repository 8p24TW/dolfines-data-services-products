from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd


# ── 8p2 service playbook — specific to actual 8p2 / Dolfines offerings ─────────
SERVICE_PLAYBOOK = {
    "solar": {
        "service_fit": "Solar performance monitoring · owner's engineering · yield assessment",
        "tool_idea": (
            "PVPAT Copilot — extend the existing PVPAT solar SCADA pipeline with AI-assisted "
            "diagnostics and auto-drafted commentary. Specific features: "
            "(1) natural-language fault summaries from inverter alarm logs ranked by revenue impact; "
            "(2) monthly PR-vs-budget variance explanation engine (irradiance, temperature, downtime split); "
            "(3) satellite-vs-on-site irradiance divergence screener with bias correction flag; "
            "(4) client-ready owner's-engineering PDF auto-assembled from structured SCADA output — "
            "eliminating manual analyst narration on recurring mandates."
        ),
    },
    "wind": {
        "service_fit": "Wind SCADA diagnostics · availability analysis · lifetime-extension advisory",
        "tool_idea": (
            "WINDPAT Copilot — layer AI-assisted diagnostics onto the 8p2 wind SCADA report pipeline. "
            "Specific features: "
            "(1) NLP fault-code enrichment mapping OEM error logs to probable component, failure mode, "
            "and downtime duration — replacing manual log triage; "
            "(2) power-curve degradation detector using rolling wind-speed-bin regression to flag "
            "sub-contracted performance vs. OEM guarantee; "
            "(3) RPM/pitch scatter pattern classifier detecting pitch runaway, curtailment mode, "
            "or drivetrain anomalies before they appear in availability losses; "
            "(4) auto-drafted WINDPAT report commentary, turning structured analysis output into "
            "client-ready narrative for the 8p2 wind performance report template."
        ),
    },
    "bess": {
        "service_fit": "BESS sizing · dispatch review · O&M and augmentation advisory",
        "tool_idea": (
            "BESS Technical Review Copilot — AI-assisted workbench for 8p2 BESS advisory mandates. "
            "Specific features: "
            "(1) SOH-adjusted capacity forecast from degradation history, with augmentation trigger "
            "modelled against projected revenue loss from capacity fade; "
            "(2) dispatch-strategy back-tester comparing contracted vs. actual cycling behaviour "
            "against spot and balancing-market price curves; "
            "(3) commissioning and O&M documentation checker scoring completeness against the "
            "8p2 BESS technical review checklist and relevant IEC / supplier spec; "
            "(4) monthly performance pack auto-generator for BESS O&M reporting mandates."
        ),
    },
    "due_diligence": {
        "service_fit": "Renewable energy technical due diligence · data-room review · investment memo support",
        "tool_idea": (
            "8p2 DD Copilot — AI-assisted data-room reviewer for solar, wind, and BESS acquisition mandates. "
            "Specific features: "
            "(1) document classifier and gap-list generator comparing uploaded files against a "
            "configurable 8p2 DD checklist (yield report, O&M contract, insurance, permits, grid connection); "
            "(2) yield-report analyser extracting P50/P90, loss tree assumptions, curtailment flags, "
            "and comparing against 8p2 benchmark ranges; "
            "(3) cross-technology red-flag synthesis for investment-committee memo drafting — "
            "ranking findings by materiality and deal risk; "
            "(4) precedent-comparison engine linking project assumptions to past 8p2 mandate outcomes."
        ),
    },
    "reporting": {
        "service_fit": "Portfolio reporting · recurring analytics · SCADA-to-report automation",
        "tool_idea": (
            "8p2 Report Factory — scheduling layer on top of PVPAT and WINDPAT to automate recurring "
            "monthly and quarterly client reporting with no manual analyst input. "
            "Specific features: "
            "(1) cron-driven data ingestion, chart generation, and PDF rendering pipeline — "
            "same output quality as current hand-crafted 8p2 reports; "
            "(2) variance commentary engine explaining month-on-month changes in PR, availability, "
            "or energy output using structured data, not manual narration; "
            "(3) multi-site portfolio rollup combining site-level KPIs into an executive-summary "
            "pack for fund or asset-manager clients; "
            "(4) client-portal delivery with version history, PDF archive, and audit trail."
        ),
    },
    "tender": {
        "service_fit": "RFP / tender response · bid qualification · advisory scope definition",
        "tool_idea": (
            "8p2 Tender Copilot — AI-assisted bid assembly for solar, wind, and BESS advisory RFPs. "
            "Specific features: "
            "(1) scope and requirements extractor from tender documents, producing a structured "
            "checklist of deliverables and evaluation criteria; "
            "(2) precedent-matcher pulling relevant past project summaries, team CVs, and "
            "methodology templates from the 8p2 knowledge base; "
            "(3) technical section drafter pre-filled with 8p2 standard methodology "
            "(PVPAT / WINDPAT / BESS review) adjusted to mandate-specific technology and size; "
            "(4) bid qualification scorer estimating win probability, margin, and strategic "
            "fit from project and client attributes — helping prioritise which tenders to pursue."
        ),
    },
    "agents": {
        "service_fit": "AI agent workflows · multi-step automation · internal operations",
        "tool_idea": (
            "8p2 Internal Ops Agent — agentic workflow layer for repeatable internal tasks. "
            "Specific candidates: "
            "(1) monthly report dispatch agent that ingests SCADA data, runs PVPAT/WINDPAT, "
            "renders the PDF, and emails the client pack automatically; "
            "(2) DD data-room triage agent that downloads, classifies, and flags gaps in "
            "uploaded documents overnight; "
            "(3) tender monitoring agent scanning procurement portals for new RFPs matching "
            "8p2's service scope and alerting the business development team."
        ),
    },
    "knowledge": {
        "service_fit": "Internal knowledge management · methodology reuse · analyst productivity",
        "tool_idea": (
            "8p2 Knowledge Assistant — internal RAG system over 8p2 methodology documents, "
            "past reports, and technical templates. "
            "Specific use cases: "
            "(1) analyst asks 'what loss assumptions did we use for agrivoltaic yield in France?' "
            "and gets a direct answer with source reference; "
            "(2) BD team retrieves relevant past mandate summaries for a new client pitch in seconds; "
            "(3) new analyst onboarded against 8p2's PVPAT/WINDPAT methodology documentation "
            "via Q&A rather than manual reading."
        ),
    },
}


def _strip_tags(raw: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", raw or "")
    return html.unescape(re.sub(r"\s+", " ", clean)).strip()


def _extract_section(html_text: str, start_label: str, end_label: str | None) -> str:
    start = html_text.find(start_label)
    if start < 0:
        return ""
    end = html_text.find(end_label, start + len(start_label)) if end_label else -1
    if end < 0:
        return html_text[start:]
    return html_text[start:end]


def load_daily_pulse_signals(daily_pulse_dir: Path) -> dict[str, list[str]]:
    preview_path = Path(daily_pulse_dir) / "digest_preview.html"
    if not preview_path.exists():
        return {"solar": [], "bess": [], "wind": []}
    text = preview_path.read_text(encoding="utf-8", errors="ignore")
    sections = {
        "solar": _extract_section(text, "☀️&nbsp; Solar PV",      "🔋&nbsp; Battery / BESS"),
        "bess":  _extract_section(text, "🔋&nbsp; Battery / BESS", "💨&nbsp; Wind"),
        "wind":  _extract_section(text, "💨&nbsp; Wind",           "www.8p2.fr"),
    }
    signals: dict[str, list[str]] = {}
    for key, section in sections.items():
        titles = []
        for href, inner in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', section, flags=re.S):
            title = _strip_tags(inner)
            if not title:
                continue
            lowered = title.lower()
            if "article" in lowered or "8.2 advisory" in lowered or "dolfines" in lowered:
                continue
            if href.startswith("mailto:") or "8p2.fr" in href:
                continue
            if title not in titles:
                titles.append(title)
            if len(titles) >= 3:
                break
        signals[key] = titles
    return signals


def _sector_for_topic(topic: str, category: str, summary: str) -> str | None:
    haystack = f"{topic} {category} {summary}".lower()
    # BESS first (to avoid "wind storage" matching wind)
    if any(t in haystack for t in ["battery", "bess", "storage", "dispatch", "augmentation", "hybri"]):
        return "bess"
    # Wind
    if any(t in haystack for t in ["wind", "scada", "turbine", "power curve", "availability", "lifetime", "rpm"]):
        return "wind"
    # Solar
    if any(t in haystack for t in ["solar", "pv", "photovoltaic", "agrivolta", "irradiance", "yield"]):
        return "solar"
    # Due diligence
    if "due diligence" in haystack or "dd ai" in haystack or "data room" in haystack:
        return "due_diligence"
    # Reporting
    if "report" in haystack or "dashboard" in haystack or "portfolio" in haystack:
        return "reporting"
    # Tender/RFP
    if any(t in haystack for t in ["rfp", "tender", "proposal", "bid"]):
        return "tender"
    # Agents
    if any(t in haystack for t in ["agent", "agentic", "autonomous", "multi-step", "workflow automat"]):
        return "agents"
    # Knowledge management / RAG
    if any(t in haystack for t in ["knowledge", "rag", "retrieval", "internal search", "enterprise search"]):
        return "knowledge"
    return None


def enrich_topics_with_8p2_context(topics: pd.DataFrame, daily_pulse_signals: dict[str, list[str]]) -> pd.DataFrame:
    if topics.empty:
        return topics
    enriched = topics.copy()
    service_fit_col     = []
    pulse_signal_col    = []
    enriched_tool_idea  = []

    for row in enriched.itertuples(index=False):
        sector   = _sector_for_topic(row.topic, row.category, row.summary)
        playbook = SERVICE_PLAYBOOK.get(sector or "")
        if playbook:
            base_tool = playbook["tool_idea"]
            fit       = playbook["service_fit"]
        else:
            base_tool = row.tool_idea
            fit       = "General AI trend — exploratory fit for 8p2"

        pulse_titles = daily_pulse_signals.get(sector or "", []) if sector in {"solar", "wind", "bess"} else []
        pulse_note   = " | ".join(pulse_titles[:2]) if pulse_titles else ""
        if pulse_note:
            enriched_tool_idea.append(f"{base_tool}  ·  Current Daily Pulse signals: {pulse_note}.")
        else:
            enriched_tool_idea.append(base_tool)
        service_fit_col.append(fit)
        pulse_signal_col.append(pulse_note)

    enriched["service_fit"] = service_fit_col
    enriched["pulse_signal"] = pulse_signal_col
    enriched["tool_idea"]   = enriched_tool_idea
    return enriched
