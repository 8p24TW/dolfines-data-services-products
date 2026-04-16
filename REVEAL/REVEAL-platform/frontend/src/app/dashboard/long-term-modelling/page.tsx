"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useSites } from "@/hooks/useSites";
import type { Site } from "@/types/site";

function SiteTypeBadge({ siteType }: { siteType: "solar" | "wind" }) {
  return (
    <span
      className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
        siteType === "solar"
          ? "border border-orange-300/20 bg-orange-400/15 text-orange-100"
          : "border border-sky-300/20 bg-sky-400/15 text-sky-100"
      }`}
    >
      {siteType === "solar" ? "Solar PV" : "Wind"}
    </span>
  );
}

type SavedLongTermSetup = {
  latitude?: string;
  longitude?: string;
  savedAt?: string;
  updatedAt?: string;
  lastOpenedAt?: string;
};

type SiteCardSite = Site & {
  displayLat: number;
  displayLon: number;
  hasSavedSetup: boolean;
  savedSetupAt: number | null;
};

function parseSavedCoordinate(value?: string) {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseSavedTimestamp(saved: SavedLongTermSetup) {
  const candidate = saved.savedAt ?? saved.updatedAt ?? saved.lastOpenedAt;
  if (!candidate) return null;
  const timestamp = Date.parse(candidate);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function renderSiteCards(sites: SiteCardSite[]) {
  return (
    <div className="mt-5 overflow-hidden rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)]">
      {sites.map((site) => (
        <Link
          key={site.id}
          href={`/dashboard/site/${site.id}/long-term-modelling`}
          className="grid gap-3 border-t border-white/8 px-4 py-3 transition hover:bg-[rgba(255,255,255,0.06)] md:grid-cols-[1.3fr_0.8fr_1fr_0.9fr_auto] md:items-center first:border-t-0"
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
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/45">Coordinates</p>
            <p className="mt-1 text-sm font-semibold text-white">
              {site.displayLat.toFixed(3)}, {site.displayLon.toFixed(3)}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/45">Technology</p>
            <p className="mt-1 text-sm font-semibold text-white">{site.technology}</p>
          </div>
          <div className="flex items-center justify-between gap-3 md:justify-end">
            <SiteTypeBadge siteType={site.site_type} />
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-100">Open</span>
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function LongTermLandingPage() {
  const { sites, isLoading } = useSites();
  const [savedSetupBySiteId, setSavedSetupBySiteId] = useState<Record<string, SavedLongTermSetup>>({});

  useEffect(() => {
    if (typeof window === "undefined" || sites.length === 0) return;

    const nextSavedSetupBySiteId: Record<string, SavedLongTermSetup> = {};
    for (const site of sites) {
      const raw = window.localStorage.getItem(`reveal-long-term-${site.id}`);
      if (!raw) continue;
      try {
        nextSavedSetupBySiteId[site.id] = JSON.parse(raw) as SavedLongTermSetup;
      } catch {
        // Ignore malformed local data and fall back to persisted site fields.
      }
    }

    setSavedSetupBySiteId(nextSavedSetupBySiteId);
  }, [sites]);

  const siteCards = useMemo<SiteCardSite[]>(() => {
    return sites.map((site) => {
      const savedSetup = savedSetupBySiteId[site.id];
      const savedLat = parseSavedCoordinate(savedSetup?.latitude);
      const savedLon = parseSavedCoordinate(savedSetup?.longitude);
      return {
        ...site,
        displayLat: savedLat ?? site.lat,
        displayLon: savedLon ?? site.lon,
        hasSavedSetup: Boolean(savedSetup),
        savedSetupAt: savedSetup ? parseSavedTimestamp(savedSetup) : null,
      };
    });
  }, [savedSetupBySiteId, sites]);

  const savedSites = useMemo(
    () =>
      siteCards
        .filter((site) => site.hasSavedSetup)
        .sort((a, b) => {
          if (a.savedSetupAt && b.savedSetupAt) return b.savedSetupAt - a.savedSetupAt;
          if (a.savedSetupAt) return -1;
          if (b.savedSetupAt) return 1;
          return a.display_name.localeCompare(b.display_name);
        }),
    [siteCards]
  );

  const otherSites = useMemo(
    () => siteCards.filter((site) => !site.hasSavedSetup).sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [siteCards]
  );

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image
          src="/brand/long-term-hero.jpg"
          alt="Long-term modelling background"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.92),rgba(4,24,36,0.82),rgba(4,24,36,0.74))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label="Back to dashboard" />

        <section className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">Long-Term Modelling</h1>
              <p className="max-w-4xl text-sm leading-7 text-slate-200/84">
                Choose a site to upload measured SCADA data, confirm assumptions, fetch reference weather, screen bad data, review fit and yield,
                then generate the long-term production output for storage or hybridization studies.
              </p>
            </div>
            <Link href="/dashboard/knowledge-base">
              <Button variant="secondary">Open Resource Database</Button>
            </Link>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
            <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Workflow overview</h2>
            <ol className="mt-5 space-y-2">
              {[ 
                "Upload actual data and confirm the detected SCADA mappings",
                "Confirm site assumptions and fetch ERA5-Land reference weather",
                "Screen bad data before the calibration step",
                "Review fit and yield before confirming the yield basis",
                "Confirm the yield basis and generate the long-term output file",
              ].map((item, index) => (
                <li key={item} className="grid grid-cols-[auto_1fr] gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                  <span className="mt-0.5 text-xs font-semibold uppercase tracking-[0.2em] text-orange-100/75">{`${index + 1}.`}</span>
                  <span className="text-sm font-medium text-white">{item}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
            <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Current scope</h2>
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/8 p-4">
                <p className="text-sm font-semibold text-white">Operational extrapolation</p>
                <p className="mt-2 text-xs leading-6 text-slate-200/80">
                  The first release is focused on extrapolating the observed operational behavior and correlating it against long-term reference irradiance.
                </p>
              </div>
              <div className="rounded-2xl border border-amber-300/20 bg-amber-500/8 p-4">
                <p className="text-sm font-semibold text-white">P50 optimization follows next</p>
                <p className="mt-2 text-xs leading-6 text-slate-200/80">
                  A cleaner P50-oriented normalized case will be added once the first correlation and export path is stable.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Saved sites</h2>
              <p className="mt-2 text-sm text-slate-200/78">Resume long-term modelling from the sites that already have saved setup in this browser.</p>
            </div>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
              {savedSites.length} saved
            </span>
          </div>

          {isLoading ? (
            <p className="mt-6 text-sm text-slate-400">Loading sites…</p>
          ) : savedSites.length > 0 ? (
            renderSiteCards(savedSites)
          ) : (
            <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/4 p-5 text-sm leading-7 text-slate-300/78">
              No saved long-term setup found yet. Open any site once, save its modelling setup, and it will be promoted here.
            </div>
          )}
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">All configured sites</h2>
                <p className="mt-2 text-sm text-slate-200/78">Choose an existing REVEAL site, even if it has not been saved yet in the long-term workflow.</p>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/70">
                {sites.length} sites
              </span>
            </div>

            {isLoading ? (
              <p className="mt-6 text-sm text-slate-400">Loading sites…</p>
            ) : otherSites.length > 0 ? (
              renderSiteCards(otherSites)
            ) : (
              <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/4 p-5 text-sm leading-7 text-slate-300/78">
                Every available site is already represented in the saved-sites section above.
              </div>
            )}
          </div>

          <div className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/50">New site</p>
            <h2 className="mt-2 font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Create another site</h2>
            <p className="mt-3 text-sm leading-7 text-slate-200/82">
              If the asset is not yet configured in REVEAL, create it first so the long-term workflow inherits the right technology, capacities, and
              coordinates before you upload measured data.
            </p>
            <div className="mt-5">
              <Link href="/dashboard/site/new/edit">
                <Button variant="primary">Add new site</Button>
              </Link>
            </div>
            <div className="mt-5 rounded-2xl border border-emerald-300/20 bg-emerald-500/8 p-4">
              <p className="text-sm font-semibold text-white">Existing sites stay first</p>
              <p className="mt-2 text-xs leading-6 text-slate-200/80">
                Saved sites are surfaced above first, then the rest of the configured portfolio, and only then the create-new option.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
