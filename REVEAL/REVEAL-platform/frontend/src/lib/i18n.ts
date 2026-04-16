"use client";

import { createContext, createElement, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import en from "@/i18n/en";
import fr from "@/i18n/fr";
import de from "@/i18n/de";

type Lang = "en" | "fr" | "de";
type Translations = typeof en;

const translations: Record<Lang, Translations> = { en, fr, de };

const I18nContext = createContext<{
  lang: Lang;
  t: (key: string) => string;
  setLang: (l: Lang) => void;
}>({
  lang: "en",
  t: (k) => k,
  setLang: () => {},
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("reveal_lang");
    if (saved === "en" || saved === "fr" || saved === "de") {
      setLang(saved);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("reveal_lang", lang);
  }, [lang]);

  function t(key: string): string {
    const keys = key.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let val: any = translations[lang];
    for (const k of keys) {
      val = val?.[k];
      if (val === undefined) break;
    }
    if (typeof val === "string") return val;
    // Fallback to English
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let fallback: any = translations["en"];
    for (const k of keys) {
      fallback = fallback?.[k];
    }
    return typeof fallback === "string" ? fallback : key;
  }

  return createElement(I18nContext.Provider, { value: { lang, t, setLang } }, children);
}

export function useTranslation() {
  return useContext(I18nContext);
}
