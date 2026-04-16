"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/Button";
import { BrandLockup } from "@/components/layout/BrandLockup";
import { useTranslation } from "@/lib/i18n";

const LOGIN_COPY = {
  en: {
    title: "REVEAL",
    titleSecondary: "Renewable Energy Valuation, Evaluation and Analytics Lab",
    subtitle: "Solar PV and wind performance analysis, long-term normalization, electricity price forecasting, BESS retrofit screening and equipment intelligence.",
    signIn: "Sign in with Microsoft",
    powered: "Powered by 8p2 Advisory",
    helper: "Use your Dolfines Microsoft account to access the platform securely.",
    invalid: "Unable to start Microsoft sign-in right now.",
  },
  fr: {
    title: "REVEAL",
    titleSecondary: "Renewable Energy Valuation, Evaluation and Analytics Lab",
    subtitle: "Analyse de performance solaire PV et éolienne, normalisation long terme, prévision des prix de l'électricité, dimensionnement de retrofit BESS et intelligence équipement.",
    signIn: "Se connecter avec Microsoft",
    powered: "Powered by 8p2 Advisory",
    helper: "Utilisez votre compte Microsoft Dolfines pour accéder à la plateforme en toute sécurité.",
    invalid: "Impossible de lancer la connexion Microsoft pour le moment.",
  },
  de: {
    title: "REVEAL",
    titleSecondary: "Renewable Energy Valuation, Evaluation and Analytics Lab",
    subtitle: "Solar- und Windleistungsanalyse, Langfristnormalisierung, Strompreisvorhersage, BESS-Retrofit-Screening und Anlagenintelligenz.",
    signIn: "Mit Microsoft anmelden",
    powered: "Powered by 8p2 Advisory",
    helper: "Melden Sie sich mit Ihrem Dolfines-Microsoft-Konto sicher an.",
    invalid: "Microsoft-Anmeldung konnte gerade nicht gestartet werden.",
  },
} as const;

export default function LoginPage() {
  const { lang, setLang } = useTranslation();
  const [displayLang, setDisplayLang] = useState(lang);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDisplayLang(lang);
  }, [lang]);

  const copy = LOGIN_COPY[displayLang] ?? LOGIN_COPY.en;

  async function handleAzureLogin() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await signIn("azure-ad", {
        callbackUrl: "/dashboard",
        redirect: false,
      });

      if (result?.error) {
        setError(copy.invalid);
        return;
      }

      if (result?.url) {
        window.location.href = result.url;
        return;
      }

      setError(copy.invalid);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <Image
        src="/brand/login-hero.jpg"
        alt="Wind farm background"
        fill
        priority
        className="object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(2,18,28,0.9),rgba(5,30,45,0.66),rgba(240,120,32,0.18))]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_42%)]" />
      <div className="absolute left-8 top-7 z-10 flex items-center gap-3 whitespace-nowrap">
        <BrandLockup href="/login" />
        <span className="text-sm font-medium text-white/75 drop-shadow">
          Renewable Energy Valuation, Evaluation and Analytics Lab
        </span>
      </div>
      <div className="absolute right-6 top-6 z-20 flex items-center gap-2 rounded-full border border-white/20 bg-[rgba(3,20,31,0.78)] px-2.5 py-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.22)] backdrop-blur-md">
        <span className="text-[10px] font-semibold uppercase tracking-[0.26em] text-white/70">
          Language
        </span>
        <div className="flex items-center gap-1">
          {(["en", "fr", "de"] as const).map((option) => {
            const active = displayLang === option;
            return (
              <button
                key={option}
                type="button"
                onClick={() => {
                  setDisplayLang(option);
                  setLang(option);
                }}
                className={`min-w-[34px] rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                  active
                    ? "bg-orange-DEFAULT text-white shadow-[0_8px_24px_rgba(240,120,32,0.28)]"
                    : "bg-white/6 text-white/78 hover:bg-white/12 hover:text-white"
                }`}
                aria-pressed={active}
                aria-label={`Switch language to ${option.toUpperCase()}`}
              >
                {option.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      <div key={displayLang} className="relative w-full max-w-md rounded-[28px] border border-orange-DEFAULT/25 bg-orange-DEFAULT/10 p-8 shadow-[0_32px_90px_rgba(0,0,0,0.4)] backdrop-blur-md transition-colors hover:bg-orange-DEFAULT/15">
        <div className="mb-8 text-center">
          <h1 className="font-dolfines text-5xl font-semibold tracking-[0.08em] text-white">
            {copy.title}
          </h1>
          <p className="mt-4 text-sm text-slate-200/78">
            {copy.subtitle}
          </p>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-white/14 bg-white/7 px-4 py-4 text-sm text-slate-100/88 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
            {copy.helper}
          </div>
          {error ? <p className="text-sm font-semibold text-red-400">{error}</p> : null}
          <Button
            variant="primary"
            size="lg"
            className="w-full !bg-[#F39200] hover:!bg-[#F7B540]"
            loading={submitting}
            onClick={handleAzureLogin}
          >
            {copy.signIn}
          </Button>
        </div>

        <p className="mt-6 text-center text-xs font-bold uppercase tracking-[0.18em] text-slate-300/55">
          {copy.powered}
        </p>
      </div>
    </main>
  );
}
