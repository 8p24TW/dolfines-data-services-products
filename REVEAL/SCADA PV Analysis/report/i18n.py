"""i18n.py — Internationalisation support for PVPAT report generation.

Usage:
    from report.i18n import get_translator
    t = get_translator("fr")
    title = t("cover.subtitle")
    text  = t("exec.commentary.1", mean_pr="78.2%", last_pr="77.1%", total_energy="4 321 MWh")

A key not found in the target language silently falls back to English.
A key not found in English returns the key string itself (so the report still
renders; missing translations appear as dotted identifiers).
"""
from __future__ import annotations
from typing import Callable


def get_translator(lang: str = "en") -> Callable[..., str]:
    """Return a translation callable ``t(key, **fmt_kwargs)`` for *lang*."""
    from report.translations import en as _en_mod
    en: dict[str, str] = _en_mod.STRINGS

    if lang == "en":
        target: dict[str, str] = en
    else:
        try:
            import importlib
            _mod = importlib.import_module(f"report.translations.{lang}")
            target = _mod.STRINGS
        except (ImportError, AttributeError):
            target = {}

    def t(key: str, **kwargs: str) -> str:  # noqa: ANN202
        """Look up *key*, fall back to English, apply optional format kwargs."""
        text = target.get(key) or en.get(key) or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return text

    return t
