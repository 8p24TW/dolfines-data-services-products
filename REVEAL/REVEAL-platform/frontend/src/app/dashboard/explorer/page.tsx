"use client";

import Image from "next/image";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSites } from "@/hooks/useSites";
import { ReportTypeCard } from "@/components/reports/ReportTypeCard";
import { BackLink } from "@/components/layout/BackLink";
import { useTranslation } from "@/lib/i18n";

function ExplorerPageContent() {
  const { t, lang } = useTranslation();
  const searchParams = useSearchParams();
  const initialSite = searchParams.get("siteId") ?? "";
  const { sites } = useSites();

  const [selectedSite, setSelectedSite] = useState(initialSite);
  const selectedSiteName = useMemo(
    () => sites.find((site) => site.id === selectedSite)?.display_name ?? "",
    [selectedSite, sites]
  );

  const intro =
    lang === "fr"
      ? "Choisissez un site puis le niveau d'analyse de performance souhaité. Cette page sert de point d’entrée rapide vers les diagnostics rapides, synthétiques ou complets."
      : "Choose a site, then the performance analysis depth you want. This page is the quick entry point for quick checks, summary reviews, or comprehensive diagnoses.";

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/reporting-hero.jpg" alt="Performance explorer hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.93),rgba(5,30,45,0.8),rgba(8,40,54,0.64))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink
          href={selectedSite ? `/dashboard/site/${selectedSite}` : "/dashboard"}
          label={selectedSite ? t("common.backToSite") : t("common.backToDashboard")}
        />

        <section className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-3xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
            <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">{t("explorer.title")}</h1>
            <p className="text-sm text-slate-200/82">{intro}</p>
          </div>
        </section>

        <section className="grid gap-4 rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.84)] p-5 shadow-[0_16px_40px_rgba(0,0,0,0.22)] backdrop-blur-sm">
          <label className="space-y-2">
            <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-white/55">{t("common.site")}</span>
            <select
              value={selectedSite}
              onChange={(event) => setSelectedSite(event.target.value)}
              className="h-12 w-full rounded-2xl border border-white/12 bg-[rgba(4,18,28,0.88)] px-4 text-sm font-semibold text-white outline-none transition focus:border-orange-DEFAULT focus:ring-2 focus:ring-orange-DEFAULT/30"
            >
              <option value="">{t("common.selectSite")}</option>
              {sites.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.display_name}
                </option>
                ))}
              </select>
          </label>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <ReportTypeCard
            type="daily"
            title="Quick check"
            description={selectedSiteName ? `Short-period performance check for ${selectedSiteName}.` : "Best for daily data. Fast view of availability, yield, and obvious issues."}
            href={selectedSite ? `/dashboard/site/${selectedSite}/reports/generate?type=daily` : "#"}
          />
          <ReportTypeCard
            type="monthly"
            title="Summary review"
            description={selectedSiteName ? `Monthly or aggregated performance review for ${selectedSiteName}.` : "Best for monthly data. Summary KPIs, trends, and plant-level context."}
            href={selectedSite ? `/dashboard/site/${selectedSite}/reports/generate?type=monthly` : "#"}
          />
          <ReportTypeCard
            type="comprehensive"
            title="Comprehensive diagnosis"
            description={selectedSiteName ? `Deep SCADA diagnosis for ${selectedSiteName}.` : "Best for 6+ months. PR, availability, loss attribution, and improvement points."}
            href={selectedSite ? `/dashboard/site/${selectedSite}/reports/generate?type=comprehensive` : "#"}
          />
        </section>

        {!selectedSite && (
          <div className="rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.8)] p-5 text-sm text-slate-200/84 backdrop-blur-sm">
            {lang === "fr"
              ? "Sélectionnez un site pour activer les formats de rapport."
              : "Select a site to activate the performance analysis formats."}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ExplorerPage() {
  return (
    <Suspense fallback={<p className="px-8 py-8 text-sm text-slate-400">Loading reporting…</p>}>
      <ExplorerPageContent />
    </Suspense>
  );
}
