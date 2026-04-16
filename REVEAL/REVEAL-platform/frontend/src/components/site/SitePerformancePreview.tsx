"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import { WindPowerCurveChart } from "@/components/charts/WindPowerCurveChart";
import { Button } from "@/components/ui/Button";
import {
  detectWindManufacturer,
  getWindModels,
  getWindSpec,
} from "@/lib/equipment-kb";
import {
  clearPerformancePreviewSnapshot,
  loadPerformancePreviewSnapshot,
  type PerformancePreviewSnapshot,
} from "@/lib/performance-preview";
import type { Site } from "@/types/site";

const PR_DEGRADATION_PER_YEAR = 0.005;
const DAYS_PER_YEAR = 365.25;

function parseUiDate(value: string | undefined) {
  if (!value) return null;
  const [day, month, year] = value.split("/");
  if (!day || !month || !year) return null;
  const parsed = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getCurrentReferencePr(site: Site, today = new Date()) {
  const designPr = site.design_pr || 0.8;
  const cod = parseUiDate(site.cod);
  if (!cod) return designPr;
  const elapsedMs = Math.max(today.getTime() - cod.getTime(), 0);
  const elapsedDays = elapsedMs / 86_400_000;
  return designPr * Math.pow(1 - PR_DEGRADATION_PER_YEAR, elapsedDays / DAYS_PER_YEAR);
}

function inferWindCurve(site: Site) {
  const manufacturer = detectWindManufacturer(site.technology) || "Vestas";
  const candidateModel = getWindModels(manufacturer).find((model) => site.technology.toLowerCase().includes(model.toLowerCase()));
  const chosenModel = candidateModel ?? getWindModels(manufacturer)[0] ?? "V136-4.5";
  const spec = getWindSpec(manufacturer, chosenModel);
  return {
    manufacturer,
    model: chosenModel,
    ratedMw: spec?.rated_mw ?? Math.max(2, Number(site.cap_ac_kw) / 1000),
  };
}

function formatDateRange(snapshot: PerformancePreviewSnapshot) {
  if (!snapshot.dataDateRange) return "Latest completed performance-analysis snapshot";
  return `Analysed period ${snapshot.dataDateRange[0]} to ${snapshot.dataDateRange[1]}`;
}

function hasFullYearCoverage(snapshot: PerformancePreviewSnapshot) {
  return snapshot.analysedDays != null && snapshot.analysedDays >= 330;
}

function formatMonthLabel(value: string) {
  const [year, month] = value.split("-");
  if (!year || !month) return value;
  const date = new Date(`${value}-01T00:00:00`);
  return date.toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
}

function SolarPerformanceSnapshotChart({
  data,
  targetPrPct,
}: {
  data: PerformancePreviewSnapshot["recentMonthlyPr"];
  targetPrPct: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 12, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a50" />
        <XAxis
          dataKey="month"
          tick={{ fill: "#cbd5e1", fontSize: 12 }}
          tickFormatter={formatMonthLabel}
        />
        <YAxis
          yAxisId="left"
          domain={[0, 100]}
          tickFormatter={(value: number) => `${value}%`}
          tick={{ fill: "#cbd5e1", fontSize: 12 }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickFormatter={(value: number) => `${Math.round(value)}`}
          tick={{ fill: "#cbd5e1", fontSize: 12 }}
        />
        <Tooltip
          contentStyle={{ background: "#0B2A3D", border: "1px solid #003366", borderRadius: 8, color: "#f8fafc" }}
          labelFormatter={(label) => formatMonthLabel(String(label))}
          formatter={(value: number, name: string) => {
            if (name === "Site PR") return [`${value.toFixed(1)}%`, name];
            if (name === "Irradiation") return [`${value.toFixed(1)} kWh/m²`, name];
            return [value, name];
          }}
        />
        <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} />
        <ReferenceLine
          yAxisId="left"
          y={targetPrPct}
          stroke="#F39200"
          strokeDasharray="6 4"
          label={{ value: `Reference ${targetPrPct.toFixed(1)}%`, position: "insideTopRight", fill: "#F39200", fontSize: 11 }}
        />
        <Bar yAxisId="left" dataKey="PR_pct" name="Site PR" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={28} />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="irrad_kwh_m2"
          name="Irradiation"
          stroke="#f8b84e"
          strokeWidth={2.5}
          dot={{ r: 3, strokeWidth: 0, fill: "#f8b84e" }}
          activeDot={{ r: 5 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function SitePerformancePreview({ site }: { site: Site }) {
  const [snapshot, setSnapshot] = useState<PerformancePreviewSnapshot | null>(null);
  const targetPrPct = getCurrentReferencePr(site) * 100;

  useEffect(() => {
    setSnapshot(loadPerformancePreviewSnapshot(site.id));
  }, [site.id]);

  if (site.site_type === "wind") {
    const curve = inferWindCurve(site);
    return (
      <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-5">
        <div className="mb-4">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">Wind Performance Preview</h2>
          <p className="mt-1 text-sm text-slate-400">
            Indicative power curve for {curve.manufacturer} {curve.model}
          </p>
        </div>
        <WindPowerCurveChart manufacturer={curve.manufacturer} ratedMw={curve.ratedMw} />
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-5">
        <div className="mb-4">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">Solar Performance Preview</h2>
          <p className="mt-1 text-sm text-slate-400">
            Run performance analysis to see the latest site snapshot here.
          </p>
        </div>
        <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.03] p-6 text-sm text-slate-300">
          REVEAL has not saved a completed performance-analysis snapshot for this site yet.
          <div className="mt-4">
            <Link href={`/dashboard/site/${site.id}/reports/generate?type=comprehensive`}>
              <Button variant="primary" size="sm">Run performance analysis</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">Solar Performance Preview</h2>
          <p className="mt-1 text-sm text-slate-400">
            {formatDateRange(snapshot)}. Updated {new Date(snapshot.generatedAt).toLocaleString()}.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            clearPerformancePreviewSnapshot(site.id);
            setSnapshot(null);
          }}
        >
          Clear performance preview
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Latest Annual PR</p>
          <p className="mt-2 text-2xl font-semibold text-white">
            {snapshot.latestAnnualPrPct != null ? `${snapshot.latestAnnualPrPct.toFixed(1)}%` : "—"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Mean Availability</p>
          <p className="mt-2 text-2xl font-semibold text-white">{snapshot.meanAvailabilityPct.toFixed(1)}%</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Site Specific Yield</p>
          <p className="mt-2 text-2xl font-semibold text-white">
            {snapshot.siteSpecificYieldAnnualizedKwhKwp != null ? `${snapshot.siteSpecificYieldAnnualizedKwhKwp.toFixed(1)} kWh/kWp/yr` : "—"}
          </p>
          <p className="mt-2 text-xs text-slate-400">
            {hasFullYearCoverage(snapshot)
              ? "Annualised from roughly a full year of analysed data."
              : "Annualised from a partial-year dataset. Seasonality may affect comparability."}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Whole-Site Outages</p>
          <p className="mt-2 text-2xl font-semibold text-white">{snapshot.wholeSiteEvents}</p>
          <p className="mt-2 text-xs text-slate-400">
            Daytime periods where all mapped power channels were effectively offline together.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.95fr)]">
        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Monthly Site PR vs Reference</p>
              <p className="mt-1 text-sm text-slate-300">Recent monthly site PR against the COD-adjusted reference PR, with irradiation as context.</p>
            </div>
            <p className="text-sm font-semibold text-white">Reference {targetPrPct.toFixed(1)}%</p>
          </div>
          <SolarPerformanceSnapshotChart data={snapshot.recentMonthlyPr} targetPrPct={targetPrPct} />
          <p className="mt-3 text-xs text-slate-400">
            This snapshot stays in place until REVEAL runs a newer completed performance analysis for this site.
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Snapshot Highlights</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-xl border border-white/8 bg-navy-dark/65 p-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Power Data Availability</p>
              <p className="mt-2 text-lg font-semibold text-white">{snapshot.powerDataPct.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl border border-white/8 bg-navy-dark/65 p-3">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Irradiance Availability</p>
              <p className="mt-2 text-lg font-semibold text-white">{snapshot.irradiancePct.toFixed(1)}%</p>
            </div>
          </div>

          <div className="mt-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Top Findings</p>
            {snapshot.topFindings.length ? (
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {snapshot.topFindings.map((finding, index) => (
                  <li key={`${index}-${finding}`} className="rounded-xl border border-white/8 bg-navy-dark/65 p-3">
                    {finding}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-slate-300">The last run did not store any punchlist findings.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
