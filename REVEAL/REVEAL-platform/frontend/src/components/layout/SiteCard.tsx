"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { loadPerformancePreviewSnapshot, type PerformancePreviewSnapshot } from "@/lib/performance-preview";
import type { Site } from "@/types/site";
import { useTranslation } from "@/lib/i18n";

interface SiteCardProps {
  site: Site;
}

function BessIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3.5" y="6.5" width="16" height="11" rx="2.2" />
      <path d="M19.5 10h1.75a1.25 1.25 0 0 1 0 2.5H19.5" />
      <path d="M8.5 10.5l2-2.5v2h2L10.5 13v-2h-2z" />
    </svg>
  );
}

const statusColor = {
  operational: "green",
  maintenance: "amber",
  offline: "red",
} as const;

export function SiteCard({ site }: SiteCardProps) {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<PerformancePreviewSnapshot | null>(null);

  useEffect(() => {
    setSnapshot(loadPerformancePreviewSnapshot(site.id));
  }, [site.id]);

  const siteLabel = site.site_type === "wind" ? "Wind" : "Solar PV";
  const capacityLabel = site.cap_ac_kw >= 1000 ? `${(site.cap_ac_kw / 1000).toFixed(1)} MW` : `${site.cap_ac_kw} kW`;
  const siteHref = `/dashboard/site/${site.id}`;
  const performanceState = useMemo(() => {
    if (!snapshot) {
      return { label: "Run perf analysis", tone: "idle" as const };
    }
    const pr = snapshot.latestAnnualPrPct;
    if (pr == null) {
      return { label: "Analysis ready", tone: "warning" as const };
    }
    if (pr >= 80) {
      return { label: `On target · ${pr.toFixed(1)}% PR`, tone: "good" as const };
    }
    if (pr >= 72) {
      return { label: `Under review · ${pr.toFixed(1)}% PR`, tone: "warning" as const };
    }
    return { label: `Underperforming · ${pr.toFixed(1)}% PR`, tone: "danger" as const };
  }, [snapshot]);
  const runDateLabel = snapshot
    ? new Date(snapshot.generatedAt).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <Link
      href={siteHref}
      className="block rounded-2xl border border-navy-light bg-[rgba(2,13,22,0.93)] px-4 py-3 shadow-[0_18px_50px_rgba(0,0,0,0.28)] transition-all duration-200 hover:border-white/60 hover:bg-[rgba(24,52,71,1)] hover:shadow-[0_24px_66px_rgba(0,0,0,0.42)]"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(190px,1.15fr)_minmax(0,4.55fr)_auto] lg:items-center">
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-3">
            <div className="relative shrink-0">
              <span className={`inline-flex h-11 w-11 items-center justify-center rounded-full border bg-white/5 ${site.site_type === "wind" ? "border-sky-300/35 text-sky-300" : "border-orange-300/35 text-orange-300"}`}>
                {site.site_type === "wind" ? (
                  <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="8" r="1.5" />
                    <path d="M12 9.5V21" />
                    <path d="M9.8 21h4.4" />
                    <path d="M12 8L6 6.4" />
                    <path d="M12 8l3-5.2" />
                    <path d="M12 8l5.4 2.6" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v3" />
                    <path d="M12 19v3" />
                    <path d="M4.93 4.93l2.12 2.12" />
                    <path d="M16.95 16.95l2.12 2.12" />
                    <path d="M2 12h3" />
                    <path d="M19 12h3" />
                    <path d="M4.93 19.07l2.12-2.12" />
                    <path d="M16.95 7.05l2.12-2.12" />
                  </svg>
                )}
              </span>
              {site.has_bess ? (
                <span className="absolute -bottom-1.5 -right-1.5 inline-flex h-6 w-6 items-center justify-center rounded-full border border-cyan-300/40 bg-[rgba(10,33,48,0.96)] text-cyan-200 shadow-[0_10px_24px_rgba(0,0,0,0.35)]">
                  <BessIcon className="h-3.5 w-3.5" />
                </span>
              ) : null}
            </div>
            <div className="min-w-0">
              <h3 className="truncate font-dolfines text-lg font-semibold tracking-[0.04em] text-white">{site.display_name}</h3>
              <p className="truncate whitespace-nowrap text-xs text-slate-400">
                {siteLabel}{site.has_bess ? " + BESS" : ""} · {site.region}, {site.country}
              </p>
            </div>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2.5 overflow-hidden text-[13px]">
            <span className="shrink-0 whitespace-nowrap text-slate-300">
              <span className="text-slate-400">{t("dashboard.capacity")}:</span>{" "}
              <span className="font-semibold text-white">{capacityLabel}</span>
            </span>
            <span className="min-w-0 flex-1 truncate whitespace-nowrap text-slate-300">
              <span className="text-slate-400">{t("dashboard.technology")}:</span>{" "}
              <span className="font-semibold text-white">{site.technology}</span>
            </span>
            <span className="shrink-0 whitespace-nowrap text-slate-300">
              <span className="text-slate-400">COD:</span>{" "}
              <span className="font-semibold text-white">{site.cod}</span>
            </span>
            <span className="shrink-0 whitespace-nowrap text-slate-300">
              <span className="text-slate-400">Inverters:</span>{" "}
              <span className="font-semibold text-white">{site.n_inverters}</span>
            </span>
            <span className="shrink-0 whitespace-nowrap text-slate-300">
              <span className="text-slate-400">Performance:</span>{" "}
              <span className="inline-flex items-center gap-2">
                <span
                  className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${
                    performanceState.tone === "danger"
                      ? "animate-pulse bg-danger/80 text-white shadow-[0_0_22px_rgba(198,40,40,0.28)]"
                      : performanceState.tone === "warning"
                        ? "bg-orange-DEFAULT/70 text-white"
                        : performanceState.tone === "idle"
                          ? "bg-slate-700/80 text-slate-100"
                          : "bg-green-700/70 text-white"
                  }`}
                >
                  {performanceState.label}
                </span>
                {runDateLabel ? (
                  <span className="inline-flex rounded-full border border-white/12 bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-200">
                    Run {runDateLabel}
                  </span>
                ) : null}
              </span>
            </span>
            <span className="shrink-0 whitespace-nowrap text-slate-300">
              <span className="text-slate-400">Status:</span>{" "}
              <span className="inline-flex align-middle">
                <Badge label={t(`dashboard.status.${site.status}`)} color={statusColor[site.status]} />
              </span>
            </span>
          </div>
        </div>

        <div className="flex justify-end">
          <span className="rounded-md bg-navy-light/60 px-4 py-2 text-sm font-medium text-orange-DEFAULT transition-colors hover:bg-orange-DEFAULT hover:text-white">
            {t("dashboard.viewSite")}
          </span>
        </div>
      </div>
    </Link>
  );
}
