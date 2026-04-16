"use client";

import Image from "next/image";
import Link from "next/link";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useSites } from "@/hooks/useSites";
import type { Site } from "@/types/site";

function SiteTypeBadge({ siteType }: { siteType: "solar" | "wind" }) {
  return (
    <span
      className={`inline-flex min-w-[82px] items-center justify-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
        siteType === "solar"
          ? "border border-orange-300/20 bg-orange-400/15 text-orange-100"
          : "border border-sky-300/20 bg-sky-400/15 text-sky-100"
      }`}
    >
      {siteType === "solar" ? "Solar PV" : "Wind"}
    </span>
  );
}

function renderSiteCards(sites: Site[]) {
  return (
    <div className="mt-5 overflow-hidden rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)]">
      {sites.map((site) => (
        <Link
          key={site.id}
          href={`/dashboard/site/${site.id}/reports/generate?type=comprehensive`}
          className="grid gap-3 border-t border-white/8 px-4 py-3 transition hover:bg-[rgba(255,255,255,0.06)] md:grid-cols-[1.3fr_0.8fr_0.8fr_0.8fr_170px] md:items-center first:border-t-0"
        >
          <div>
            <p className="font-dolfines text-lg font-semibold tracking-[0.04em] text-white">{site.display_name}</p>
            <p className="mt-1 text-xs text-slate-300/82">
              {site.region}, {site.country}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/45">AC</p>
            <p className="mt-1 text-sm font-semibold text-white">
              {site.cap_ac_kw >= 1000 ? `${(site.cap_ac_kw / 1000).toFixed(2)} MW` : `${site.cap_ac_kw} kW`}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/45">Technology</p>
            <p className="mt-1 text-sm font-semibold text-white">{site.technology}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/45">Workflow</p>
            <p className="mt-1 text-sm font-semibold text-white">Open performance</p>
          </div>
          <div className="flex items-center justify-between gap-3">
            <SiteTypeBadge siteType={site.site_type} />
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-100">Open</span>
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function PerformancePage() {
  const { sites, isLoading } = useSites();

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/reporting-hero.jpg" alt="Performance workflow hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.93),rgba(5,30,45,0.8),rgba(8,40,54,0.64))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label="Back to dashboard" />

        <section className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.84)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.22)] backdrop-blur-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl space-y-3">
              <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">Performance</h1>
              <p className="text-sm leading-7 text-slate-200/82">
                Choose an existing site to open the full performance workflow and review technical diagnosis, executive findings, and recoverable losses directly inside the analysis flow.
              </p>
            </div>
            <Link href="/dashboard">
              <Button variant="secondary">Create new site first</Button>
            </Link>
          </div>
        </section>
        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
            <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Performance workflow</h2>
            <ol className="mt-5 space-y-2">
              {[
                "Choose the diagnosis depth inside the workflow",
                "Upload actual SCADA data and confirm the detected columns",
                "Confirm site details and review data availability",
                "Review KPIs, executive summary, and improvement points",
                "Generate and download the summary PDF",
              ].map((item, index) => (
                <li key={item} className="grid grid-cols-[auto_1fr] gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <span className="mt-0.5 text-xs font-semibold uppercase tracking-[0.2em] text-orange-100/75">{`${index + 1}.`}</span>
                  <span className="text-sm font-medium text-white">{item}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
            <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Outputs</h2>
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/8 p-4">
                <p className="text-sm font-semibold text-white">Technical diagnosis</p>
                <p className="mt-2 text-xs leading-6 text-slate-200/80">
                  REVEAL surfaces inverter and site availability, PR, irradiation, specific yield, and data-quality checks directly inside the app.
                </p>
              </div>
              <div className="rounded-2xl border border-amber-300/20 bg-amber-500/8 p-4">
                <p className="text-sm font-semibold text-white">Improvement punchlist</p>
                <p className="mt-2 text-xs leading-6 text-slate-200/80">
                  Each run highlights the main issues and recoverable improvement points before the client-ready PDF is generated.
                </p>
              </div>
              <div className="rounded-2xl border border-red-300/20 bg-red-500/8 p-4">
                <p className="text-sm font-semibold text-white">Negative-price exposure</p>
                <p className="mt-2 text-xs leading-6 text-slate-200/80">
                  Negative-hour losses should be surfaced by the Performance analysis itself, then passed forward into the Retrofit BESS workflow.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Configured sites</h2>
              <p className="mt-2 text-sm text-slate-200/78">
                Open the performance workflow directly for an existing asset. For a new asset, create the site first so REVEAL can pull the right plant details in Step 3.
              </p>
            </div>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
              {sites.length} sites
            </span>
          </div>

          {isLoading ? (
            <p className="mt-6 text-sm text-slate-400">Loading sites…</p>
          ) : sites.length > 0 ? (
            renderSiteCards(sites.sort((a, b) => a.display_name.localeCompare(b.display_name)))
          ) : (
            <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/4 p-5 text-sm leading-7 text-slate-300/78">
              No sites are configured yet. Create the site first from the dashboard, then return here to open the performance workflow.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
