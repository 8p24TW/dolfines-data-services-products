"use client";

import { useTranslation } from "@/lib/i18n";

export function LanguageToggle() {
  const { lang, setLang } = useTranslation();
  const options = ["en", "fr", "de"] as const;

  return (
    <div className="flex rounded border border-navy-light overflow-hidden text-xs">
      {options.map((option) => (
        <button
          key={option}
          onClick={() => setLang(option)}
          className={`px-2 py-1 transition-colors ${lang === option ? "bg-orange-DEFAULT text-white" : "text-slate-400 hover:text-white"}`}
        >
          {option.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
