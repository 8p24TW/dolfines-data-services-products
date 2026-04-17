"use client";

import Image from "next/image";
import { useState, useEffect, useRef } from "react";
import { useSite } from "@/hooks/useSites";
import useSWR from "swr";
import { KpiChip } from "@/components/ui/KpiChip";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";
import { BackLink } from "@/components/layout/BackLink";
import { useTranslation } from "@/lib/i18n";
import { SitePerformancePreview } from "@/components/site/SitePerformancePreview";
import { api } from "@/lib/api";
import { ReportHistoryTable } from "@/components/reports/ReportHistoryTable";

function SiteMap({ lat, lon, displayName }: { lat: number; lon: number; displayName: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const init = (L: any) => {
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
      const map = L.map(containerRef.current!, {
        center: [lat, lon],
        zoom: 10,
        minZoom: 2,
        maxZoom: 18,
        maxBounds: [[-85.051, -180], [85.051, 180]],
        maxBoundsViscosity: 1.0,
      });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        noWrap: true,
      }).addTo(map);
      L.marker([lat, lon]).addTo(map).bindPopup(displayName);
      mapRef.current = map;
    };

    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }

    if ((window as any).L) {
      init((window as any).L);
    } else {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.onload = () => init((window as any).L);
      document.head.appendChild(script);
    }

    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [lat, lon, displayName]);

  return (
    <div
      ref={containerRef}
      className="h-[360px] w-full bg-navy-dark"
      style={{ filter: "grayscale(0.35) invert(0.78) hue-rotate(188deg) saturate(0.88) brightness(0.96) contrast(1.28)" }}
    />
  );
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

export default function SiteDetailPage({ params }: { params: { siteId: string } }) {
  const { t } = useTranslation();
  const { site, isLoading } = useSite(params.siteId);
  const { data: reportHistory = [] } = useSWR(site ? ["report-history-inline", params.siteId] : null, ([, id]) => api.reports.history(id));
  const [configView, setConfigView] = useState<"overview" | "detailed">("overview");

  if (isLoading || !site) {
    return (
      <div className="px-8 py-6">
        <p className="text-sm text-slate-400">{t("common.loading")}</p>
      </div>
    );
  }

  const statusColor = { operational: "green", maintenance: "amber", offline: "red" } as const;
  const isWind = site.site_type === "wind";
  const heroImage = isWind ? "/brand/long-term-hero.jpg" : "/brand/reporting-hero.jpg";
  const expectedAepMWh = Math.round(((site.expected_aep_gwh ?? ((site.cap_ac_kw / 1000) * 33.5)) || 0) * 1000);
  const metMastHeight = site.hub_height_m ? Math.max(80, Math.round(site.hub_height_m - 25)) : null;
  const windSpecs: Array<[string, string]> = [
    ["Technology", site.technology || "—"],
    ["Hub height", site.hub_height_m ? `${Math.round(site.hub_height_m)} m` : "—"],
    ["Met mast height", metMastHeight ? `${metMastHeight} m` : "—"],
    ["Blade tip height", site.tip_height_m ? `${Math.round(site.tip_height_m)} m` : "—"],
    ["Rotor diameter", site.rotor_diameter_m ? `${Math.round(site.rotor_diameter_m)} m` : "—"],
    ["Unit rated power", site.inv_ac_kw ? `${site.inv_ac_kw} kW` : "—"],
    ["SCADA interval", `${site.interval_min} min`],
  ];
  const solarSpecs: Array<[string, string | number]> = [
    ["Technology", site.technology],
    ["Inverter model", site.inv_model],
    ["Inverter AC (kW)", site.inv_ac_kw],
    ["Module brand", site.module_brand],
    ["Module Wp", site.module_wp],
    ["Modules", site.n_modules.toLocaleString()],
    ["Module tilt", site.module_tilt_deg != null ? `${site.module_tilt_deg} deg` : "—"],
    ["Irradiance basis", site.irradiance_basis?.toUpperCase() ?? "—"],
    ["Tariff", site.tariff_eur_mwh != null ? `${site.tariff_eur_mwh} EUR/MWh` : "—"],
    ["Timezone", site.site_timezone ?? "—"],
    ["Configured inverter DC units", site.solar_inverter_units?.length ?? 0],
    ["DC/AC ratio", site.dc_ac_ratio.toFixed(3)],
    ["SCADA interval", `${site.interval_min} min`],
    ["Irradiance threshold", `${site.irr_threshold} W/m²`],
  ];
  const inverterBreakdown = (site.solar_inverter_units ?? []).slice().sort((a, b) => a.tag.localeCompare(b.tag, undefined, { numeric: true, sensitivity: "base" }));
  const inverterBreakdownWithDerived = inverterBreakdown.map((item) => {
    const moduleCount = item.module_count != null ? item.module_count : site.module_wp > 0 ? Math.round((item.dc_capacity_kwp * 1000) / site.module_wp) : 0;
    const derivedDcCapacity = site.module_wp > 0 ? (moduleCount * site.module_wp) / 1000 : item.dc_capacity_kwp;
    return {
      ...item,
      moduleCount,
      derivedDcCapacity,
      dcAcRatio: site.inv_ac_kw > 0 ? derivedDcCapacity / site.inv_ac_kw : 0,
      shareOfSiteDcPct: site.cap_dc_kwp > 0 ? (derivedDcCapacity / site.cap_dc_kwp) * 100 : 0,
    };
  });
  const totalBreakdownModules = inverterBreakdownWithDerived.reduce((sum, item) => sum + item.moduleCount, 0);
  const totalBreakdownDcCapacity = inverterBreakdownWithDerived.reduce((sum, item) => sum + item.derivedDcCapacity, 0);
  const totalBreakdownAcCapacity = inverterBreakdownWithDerived.length * site.inv_ac_kw;
  const totalBreakdownSharePct = inverterBreakdownWithDerived.reduce((sum, item) => sum + item.shareOfSiteDcPct, 0);
  const maxInverterDcCapacity = inverterBreakdownWithDerived.length > 0 ? Math.max(...inverterBreakdownWithDerived.map((item) => item.derivedDcCapacity)) : 0;
  const dcCapacityMismatch = Math.abs(totalBreakdownDcCapacity - site.cap_dc_kwp) > 0.01;
  const moduleCountMismatch = site.n_modules > 0 && totalBreakdownModules !== site.n_modules;

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src={heroImage} alt={isWind ? "Wind site background" : "Solar site background"} fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.9),rgba(5,30,45,0.8),rgba(5,30,45,0.68))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label={t("common.backToDashboard")} />
        <div className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.76)] p-5 backdrop-blur-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-full flex-1 space-y-1 pr-2">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
              <h1 className="max-w-full break-words font-dolfines text-2xl font-semibold tracking-[0.08em] text-white sm:text-3xl">{site.display_name}</h1>
              <p className="max-w-full break-words text-sm text-slate-300">
                {site.site_type === "wind" ? "Wind" : "Solar PV"}{site.has_bess ? " + BESS" : ""} · {site.region}, {site.country} · COD {site.cod}
              </p>
            </div>
            <div className="flex items-center gap-3 self-start">
              {site.has_bess ? (
                <span className="inline-flex items-center gap-2 rounded-full border border-cyan-300/28 bg-cyan-400/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-100">
                  <BessIcon className="h-3.5 w-3.5" />
                  BESS
                </span>
              ) : null}
              <Badge label={site.status} color={statusColor[site.status]} />
              <Link href={`/dashboard/site/${site.id}/edit`}>
                <Button variant="secondary" size="sm">{t("common.edit")}</Button>
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiChip label="AC Capacity" value={site.cap_ac_kw >= 1000 ? `${(site.cap_ac_kw / 1000).toFixed(1)}` : site.cap_ac_kw} unit={site.cap_ac_kw >= 1000 ? "MW" : "kW"} />
          {isWind ? (
            <>
              <KpiChip label="Expected AEP" value={expectedAepMWh.toLocaleString()} unit="MWh" />
              <KpiChip label="Turbines" value={site.n_inverters} />
              <KpiChip label="Rotor Diameter" value={site.rotor_diameter_m ? Math.round(site.rotor_diameter_m) : "—"} unit={site.rotor_diameter_m ? "m" : undefined} />
            </>
          ) : (
            <>
              <KpiChip label="DC Capacity" value={site.cap_dc_kwp >= 1000 ? `${(site.cap_dc_kwp / 1000).toFixed(1)}` : site.cap_dc_kwp} unit={site.cap_dc_kwp >= 1000 ? "MWp" : "kWp"} />
              <KpiChip label="Inverters" value={site.n_inverters} />
              <KpiChip label="Design PR" value={`${(site.design_pr * 100).toFixed(0)}%`} />
            </>
          )}
        </div>

        <div className="rounded-xl border border-navy-light bg-navy-DEFAULT/72 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-sm font-semibold text-white">{t("common.technicalSpecifications")}</h2>
              <div className="flex rounded-full border border-white/10 bg-white/5 p-1">
                <button
                  type="button"
                  onClick={() => setConfigView("overview")}
                  className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                    configView === "overview" ? "bg-orange-DEFAULT text-white" : "text-slate-300 hover:text-white"
                  }`}
                >
                  Overview
                </button>
                <button
                  type="button"
                  onClick={() => setConfigView("detailed")}
                  className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                    configView === "detailed" ? "bg-orange-DEFAULT text-white" : "text-slate-300 hover:text-white"
                  }`}
                >
                  Detailed breakdown
                </button>
              </div>
            </div>

            {configView === "overview" ? (
              <dl className="mt-4 grid grid-cols-1 gap-x-10 gap-y-4 text-sm md:grid-cols-2 xl:grid-cols-3">
                {(isWind ? windSpecs : solarSpecs).map(([label, value]) => (
                  <div key={String(label)} className="min-w-0">
                    <dt className="text-xs text-slate-400">{label}</dt>
                    <dd className="mt-0.5 break-words text-white">{value || "—"}</dd>
                  </div>
                ))}
              </dl>
            ) : isWind ? (
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {windSpecs.map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">{label}</p>
                    <p className="mt-2 text-sm font-semibold text-white">{value || "—"}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                {dcCapacityMismatch || moduleCountMismatch ? (
                  <div className="rounded-2xl border border-amber-300/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                    <p className="font-semibold text-amber-200">Configuration mismatch warning</p>
                    <p className="mt-1">
                      {dcCapacityMismatch
                        ? `Per-inverter DC total is ${totalBreakdownDcCapacity.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWp, while site DC capacity is ${site.cap_dc_kwp.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWp.`
                        : null}
                      {dcCapacityMismatch && moduleCountMismatch ? " " : ""}
                      {moduleCountMismatch ? `Per-inverter module total is ${totalBreakdownModules.toLocaleString()}, while the site module count is ${site.n_modules.toLocaleString()}.` : null}
                    </p>
                  </div>
                ) : null}

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Configured inverter units</p>
                    <p className="mt-2 text-sm font-semibold text-white">{inverterBreakdownWithDerived.length}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Total configured inverter DC</p>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {totalBreakdownDcCapacity.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWp
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Site DC capacity</p>
                    <p className="mt-2 text-sm font-semibold text-white">{site.cap_dc_kwp.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWp</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Difference</p>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {(site.cap_dc_kwp - totalBreakdownDcCapacity).toLocaleString(undefined, { maximumFractionDigits: 2 })} kWp
                    </p>
                  </div>
                </div>

                <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)]">
                  <table className="min-w-full divide-y divide-white/10 text-sm">
                    <thead className="bg-[rgba(255,255,255,0.03)] text-left text-xs uppercase tracking-[0.18em] text-slate-400">
                        <tr>
                          <th className="px-4 py-2.5">Inverter tag</th>
                          <th className="px-4 py-2.5"># Modules</th>
                          <th className="px-4 py-2.5">AC capacity (kW)</th>
                          <th className="px-4 py-2.5">DC capacity (kWp)</th>
                          <th className="px-4 py-2.5">DC/AC ratio</th>
                          <th className="px-4 py-2.5">Share of site DC</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/6 text-white">
                      {inverterBreakdownWithDerived.length > 0 ? (
                        inverterBreakdownWithDerived.map((item) => (
                          <tr key={item.id ?? item.tag}>
                            <td className="px-4 py-2 font-semibold">{item.tag}</td>
                            <td className="px-4 py-2">
                              {item.moduleCount > 0 ? item.moduleCount.toLocaleString() : "—"}
                            </td>
                            <td className="px-4 py-2">{site.inv_ac_kw.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                            <td className="px-4 py-2">
                              <div className="min-w-[180px]">
                                <div className="flex items-center justify-between gap-3">
                                  <span>{item.derivedDcCapacity.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                                  <span className="text-xs text-slate-400">
                                    {maxInverterDcCapacity > 0 ? `${((item.derivedDcCapacity / maxInverterDcCapacity) * 100).toFixed(0)}%` : "—"}
                                  </span>
                                </div>
                                <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/8">
                                  <div
                                    className="h-full rounded-full"
                                    style={{
                                      width: maxInverterDcCapacity > 0 ? `${Math.max((item.derivedDcCapacity / maxInverterDcCapacity) * 100, 6)}%` : "0%",
                                      background:
                                        maxInverterDcCapacity > 0
                                          ? `linear-gradient(90deg, rgba(198,40,40,0.92), rgba(243,146,0,0.9) ${Math.max(((item.derivedDcCapacity / maxInverterDcCapacity) * 100) * 0.72, 20)}%, rgba(52,211,153,0.92))`
                                          : "rgba(255,255,255,0.2)",
                                    }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-2">
                              {site.inv_ac_kw > 0 ? item.dcAcRatio.toFixed(3) : "—"}
                            </td>
                            <td className="px-4 py-2">
                              {site.cap_dc_kwp > 0 ? `${item.shareOfSiteDcPct.toFixed(2)}%` : "—"}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={6} className="px-4 py-3 text-slate-300">
                            No per-inverter DC capacities have been configured yet.
                          </td>
                        </tr>
                      )}
                      {inverterBreakdownWithDerived.length > 0 ? (
                        <tr className="border-t border-white/12 bg-[rgba(255,255,255,0.03)] font-semibold">
                          <td className="px-4 py-2.5">Total</td>
                          <td className="px-4 py-2.5">{totalBreakdownModules.toLocaleString()}</td>
                          <td className="px-4 py-2.5">{totalBreakdownAcCapacity.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                          <td className="px-4 py-2.5">{totalBreakdownDcCapacity.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                          <td className="px-4 py-2.5">{totalBreakdownAcCapacity > 0 ? (totalBreakdownDcCapacity / totalBreakdownAcCapacity).toFixed(3) : "—"}</td>
                          <td className="px-4 py-2.5">{`${totalBreakdownSharePct.toFixed(2)}%`}</td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
        </div>

        <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/72 p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">Site location</h2>
              <p className="mt-1 text-sm text-slate-400">
                Regional map centered on the configured GPS coordinates at {site.lat.toFixed(4)}, {site.lon.toFixed(4)}.
              </p>
            </div>
            <a
              href={`https://www.openstreetmap.org/?mlat=${encodeURIComponent(String(site.lat))}&mlon=${encodeURIComponent(String(site.lon))}#map=6/${encodeURIComponent(String(site.lat))}/${encodeURIComponent(String(site.lon))}`}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-white/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/35 hover:text-white"
            >
              Open map
            </a>
          </div>
          <div className="overflow-hidden rounded-3xl border border-white/10 bg-navy-dark/75 shadow-[0_18px_42px_rgba(0,0,0,0.28)]">
            <SiteMap lat={site.lat} lon={site.lon} displayName={site.display_name} />
          </div>
        </div>

        <SitePerformancePreview site={site} />

        <div className="flex flex-wrap gap-3">
          <Link href={`/dashboard/site/${site.id}/reports/generate?type=comprehensive`}>
            <Button variant="primary">Performance analysis</Button>
          </Link>
          <Link href={`/dashboard/site/${site.id}/long-term-modelling`}>
            <Button variant="secondary">Long-Term Modelling</Button>
          </Link>
          <Link href="/dashboard/financials">
            <Button variant="ghost">Financials</Button>
          </Link>
          <a href="#report-history">
            <Button variant="ghost">{t("reports.history")}</Button>
          </a>
        </div>

        <div id="report-history" className="rounded-xl border border-navy-light bg-navy-DEFAULT/72 p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">{t("reports.history")}</h2>
          <div className="overflow-x-auto">
            <ReportHistoryTable reports={reportHistory} />
          </div>
        </div>
      </div>
    </div>
  );
}
