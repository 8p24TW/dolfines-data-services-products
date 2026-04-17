"use client";

import { useState, useEffect, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  Area,
  LineChart,
  BarChart,
  Bar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useSites } from "@/hooks/useSites";
import { api } from "@/lib/api";
import type { PriceForecastResult, HourlyProfileResult, HourlyProfileRow, MarketSiteContext } from "@/types/market";

// ─── Colour tokens ────────────────────────────────────────────────────────────
const ORANGE = "#F39200";
const AMBER  = "#F5B942";
const SKY    = "#38bdf8";
const RED    = "#f87171";
const GREEN  = "#34d399";
const SLATE  = "#64748b";

const TOOLTIP_STYLE = {
  contentStyle: {
    background: "rgba(3,16,26,0.95)",
    border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 12,
    fontSize: 12,
  },
  labelStyle: { color: "#e2e8f0" },
};

// ─── Annual overview charts ───────────────────────────────────────────────────

function PriceTrajectoryChart({ rows }: { rows: PriceForecastResult["rows"] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
        Price trajectory — market vs solar capture
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
          <XAxis dataKey="year" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false}
            label={{ value: "EUR/MWh", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 10, dx: -2 }}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value: number, name: string) => [
              `${value.toFixed(1)} EUR/MWh`,
              name === "avg_price_eur_mwh" ? "Market avg" : "Solar capture",
            ]}
          />
          <Legend
            formatter={(value) => (
              <span style={{ color: "#cbd5e1", fontSize: 11 }}>
                {value === "avg_price_eur_mwh" ? "Market average" : "Solar capture price"}
              </span>
            )}
          />
          <Line type="monotone" dataKey="avg_price_eur_mwh" stroke={ORANGE} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="solar_capture_price_eur_mwh" stroke={SKY} strokeWidth={2} dot={false} strokeDasharray="5 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function NegativeHoursChart({ rows }: { rows: PriceForecastResult["rows"] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
        Estimated negative-price hours per year
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={rows} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false}
            label={{ value: "hours/yr", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 10, dx: -2 }}
          />
          <Tooltip
            {...TOOLTIP_STYLE}
            cursor={{ fill: "rgba(255,255,255,0.05)" }}
            formatter={(value: number) => [`${value} h`, "Negative-price hours"]}
          />
          <Bar dataKey="negative_hours_estimate" fill={RED} fillOpacity={0.75} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MarketIndicesChart({ rows }: { rows: PriceForecastResult["rows"] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
        Market structure indices (0 → 1 scale)
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={rows} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
          <XAxis dataKey="year" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis domain={[0, 1]} tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => v.toFixed(1)} />
          <Tooltip
            {...TOOLTIP_STYLE}
            formatter={(value: number, name: string) => [
              value.toFixed(3),
              name === "pv_cannibalization_index" ? "PV cannibalization" : "BESS relief",
            ]}
          />
          <Legend
            formatter={(value) => (
              <span style={{ color: "#cbd5e1", fontSize: 11 }}>
                {value === "pv_cannibalization_index" ? "PV cannibalization index" : "BESS relief index"}
              </span>
            )}
          />
          <ReferenceLine y={0.5} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="pv_cannibalization_index" stroke={AMBER} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="bess_relief_index" stroke={GREEN} strokeWidth={2} dot={false} strokeDasharray="5 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Hourly profile chart ─────────────────────────────────────────────────────

const P_LEVEL_OPTIONS = [
  { key: "p25", label: "P25", desc: "Optimistic — 75% exceedance" },
  { key: "p50", label: "P50", desc: "Median — central scenario" },
  { key: "p75", label: "P75", desc: "Conservative — 25% exceedance" },
  { key: "p90", label: "P90", desc: "Bankable floor — 10% exceedance" },
] as const;
type PLevel = (typeof P_LEVEL_OPTIONS)[number]["key"];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const SCENARIO_OPTIONS = [
  { key: "base", label: "Base", color: SKY },
  { key: "high", label: "High", color: ORANGE },
  { key: "low", label: "Low", color: GREEN },
] as const;
type ScenarioKey = (typeof SCENARIO_OPTIONS)[number]["key"];
type HourlyPercentileKey = "p10" | PLevel;

function percentileKey(scenario: ScenarioKey, pLevel: HourlyPercentileKey) {
  if (scenario === "base") return `price_base_${pLevel}_eur_mwh` as const;
  if (scenario === "high") return `price_high_${pLevel}_eur_mwh` as const;
  return `price_low_${pLevel}_eur_mwh` as const;
}

function negativeFrequencyKey(scenario: ScenarioKey) {
  if (scenario === "base") return "freq_neg_base" as const;
  if (scenario === "high") return "freq_neg_high" as const;
  return "freq_neg_low" as const;
}

function buildScenarioCurveRows(data: HourlyProfileRow[], pLevel: PLevel) {
  return data.map((row) => ({
    hour: row.hour,
    historical: row.historical_price_eur_mwh,
    base: row[percentileKey("base", pLevel)],
    high: row[percentileKey("high", pLevel)],
    low: row[percentileKey("low", pLevel)],
  }));
}

function buildIntervalRows(data: HourlyProfileRow[], scenario: ScenarioKey) {
  return data.map((row) => {
    const p10 = row[percentileKey(scenario, "p10")];
    const p25 = row[percentileKey(scenario, "p25")];
    const p50 = row[percentileKey(scenario, "p50")];
    const p75 = row[percentileKey(scenario, "p75")];
    const p90 = row[percentileKey(scenario, "p90")];
    return {
      hour: row.hour,
      p10,
      p25,
      p50,
      p75,
      p90,
      outerBase: p90,
      outerWidth: Math.max(0, p10 - p90),
      innerBase: p75,
      innerWidth: Math.max(0, p25 - p75),
      historical: row.historical_price_eur_mwh,
    };
  });
}

function ProjectedScenarioCurvesChart({ data, pLevel }: { data: HourlyProfileRow[]; pLevel: PLevel }) {
  const chartData = useMemo(() => buildScenarioCurveRows(data, pLevel), [data, pLevel]);
  const selectedLabel = P_LEVEL_OPTIONS.find((option) => option.key === pLevel)?.label ?? "P50";

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
        <XAxis dataKey="hour" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(h) => `${h}h`} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: "EUR/MWh", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 10, dx: -2 }} />
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: number, name: string) => {
            const labels: Record<string, string> = {
              historical: "Historical median 2021-2026",
              base: `Base ${selectedLabel}`,
              high: `High ${selectedLabel}`,
              low: `Low ${selectedLabel}`,
            };
            return [`${value.toFixed(1)} EUR/MWh`, labels[name] ?? name];
          }}
          labelFormatter={(hour) => `Hour ${hour}:00`}
        />
        <Legend formatter={(value) => <span style={{ color: "#cbd5e1", fontSize: 11 }}>{value}</span>} />
        <ReferenceLine y={0} stroke="rgba(248,113,113,0.4)" strokeDasharray="4 3" />
        <Line type="monotone" dataKey="historical" stroke="rgba(226,232,240,0.7)" strokeWidth={1.8} dot={false} strokeDasharray="5 4" name="Historical median" />
        <Line type="monotone" dataKey="base" stroke={SKY} strokeWidth={2.4} dot={false} name={`Base ${selectedLabel}`} />
        <Line type="monotone" dataKey="high" stroke={ORANGE} strokeWidth={2.4} dot={false} strokeDasharray="6 3" name={`High ${selectedLabel}`} />
        <Line type="monotone" dataKey="low" stroke={GREEN} strokeWidth={2.4} dot={false} strokeDasharray="3 3" name={`Low ${selectedLabel}`} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function MonteCarloIntervalsChart({ data, scenario }: { data: HourlyProfileRow[]; scenario: ScenarioKey }) {
  const chartData = useMemo(() => buildIntervalRows(data, scenario), [data, scenario]);
  const scenarioLabel = SCENARIO_OPTIONS.find((option) => option.key === scenario)?.label ?? "Base";
  const color = SCENARIO_OPTIONS.find((option) => option.key === scenario)?.color ?? SKY;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="outerBand" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.16} />
            <stop offset="100%" stopColor={color} stopOpacity={0.06} />
          </linearGradient>
          <linearGradient id="innerBand" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.26} />
            <stop offset="100%" stopColor={color} stopOpacity={0.12} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
        <XAxis dataKey="hour" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(h) => `${h}h`} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: "EUR/MWh", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 10, dx: -2 }} />
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: number, name: string) => {
            const labels: Record<string, string> = {
              p10: `${scenarioLabel} P10`,
              p25: `${scenarioLabel} P25`,
              p50: `${scenarioLabel} P50`,
              p75: `${scenarioLabel} P75`,
              p90: `${scenarioLabel} P90`,
              historical: "Historical median 2021-2026",
            };
            return [`${value.toFixed(1)} EUR/MWh`, labels[name] ?? name];
          }}
          labelFormatter={(hour) => `Hour ${hour}:00`}
        />
        <ReferenceLine y={0} stroke="rgba(248,113,113,0.4)" strokeDasharray="4 3" />
        <Area type="monotone" dataKey="outerBase" fill="none" stroke="none" stackId="outer" legendType="none" />
        <Area type="monotone" dataKey="outerWidth" fill="url(#outerBand)" stroke="none" stackId="outer" name="P10-P90 band" legendType="none" />
        <Area type="monotone" dataKey="innerBase" fill="none" stroke="none" stackId="inner" legendType="none" />
        <Area type="monotone" dataKey="innerWidth" fill="url(#innerBand)" stroke="none" stackId="inner" name="P25-P75 band" legendType="none" />
        <Line type="monotone" dataKey="historical" stroke="rgba(226,232,240,0.5)" strokeWidth={1.4} dot={false} strokeDasharray="5 4" name="Historical median" />
        <Line type="monotone" dataKey="p50" stroke={color} strokeWidth={2.6} dot={false} name={`${scenarioLabel} P50`} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function NegativeProbabilityChart({ data, scenario }: { data: HourlyProfileRow[]; scenario: ScenarioKey }) {
  const scenarioLabel = SCENARIO_OPTIONS.find((option) => option.key === scenario)?.label ?? "Base";
  const color = SCENARIO_OPTIONS.find((option) => option.key === scenario)?.color ?? SKY;
  const key = negativeFrequencyKey(scenario);
  const chartData = useMemo(
    () => data.map((row) => ({ hour: row.hour, negativeRiskPct: row[key] * 100 })),
    [data, key]
  );

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
        <XAxis dataKey="hour" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(h) => `${h}h`} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} label={{ value: "% negative", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 10, dx: -2 }} />
        <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: "rgba(240,120,32,0.06)" }} formatter={(value: number) => [`${value.toFixed(1)}%`, `${scenarioLabel} negative-price probability`]} labelFormatter={(hour) => `Hour ${hour}:00`} />
        <Bar dataKey="negativeRiskPct" fill={color} fillOpacity={0.72} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Hourly profile section ───────────────────────────────────────────────────

function HourlyProfileSection() {
  const [year, setYear] = useState(2027);
  const [month, setMonth] = useState(6);
  const [dayType, setDayType] = useState<"ouvre" | "weekend">("ouvre");
  const [scenario, setScenario] = useState<ScenarioKey>("base");
  const [pLevel, setPLevel] = useState<PLevel>("p50");
  const [profile, setProfile] = useState<HourlyProfileResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.market.hourlyProfile({ year, month, day_type: dayType, scenario });
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load hourly profile.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-load on mount and when controls change
  useEffect(() => {
    loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month, dayType, scenario]);

  const years = Array.from({ length: 20 }, (_, i) => 2027 + i);

  return (
    <section className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">
            REVEAL market intelligence
          </p>
          <h2 className="font-dolfines mt-1 text-xl font-semibold tracking-[0.06em] text-white">
            Projected Day-Ahead Profiles
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            Full hourly day-ahead profile browser from the consultancy projection set, including projected scenario curves, Monte Carlo uncertainty intervals, and negative-price probability by hour.
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-slate-400">Year</span>
          <select
            className="rounded-lg border border-navy-light bg-navy-dark px-3 py-1.5 text-sm text-slate-100"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-slate-400">Month</span>
          <select
            className="rounded-lg border border-navy-light bg-navy-dark px-3 py-1.5 text-sm text-slate-100"
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            {MONTH_NAMES.map((label, index) => (
              <option key={label} value={index + 1}>{label}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-slate-400">Profile type</span>
          <select
            className="rounded-lg border border-navy-light bg-navy-dark px-3 py-1.5 text-sm text-slate-100"
            value={dayType}
            onChange={(e) => setDayType(e.target.value as "ouvre" | "weekend")}
          >
            <option value="ouvre">Workday</option>
            <option value="weekend">Weekend / holiday</option>
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-slate-400">Scenario</span>
          <select
            className="rounded-lg border border-navy-light bg-navy-dark px-3 py-1.5 text-sm text-slate-100"
            value={scenario}
            onChange={(e) => setScenario(e.target.value as "base" | "high" | "low")}
          >
            <option value="base">Base (+0.5%/yr)</option>
            <option value="high">High (+1.5%/yr)</option>
            <option value="low">Low (−1.5%/yr)</option>
          </select>
        </label>

        {/* P-level selector */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-slate-400">P-level</span>
          <div className="flex gap-1">
            {P_LEVEL_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                title={opt.desc}
                onClick={() => setPLevel(opt.key)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                  pLevel === opt.key
                    ? "bg-orange-DEFAULT/25 text-orange-200 ring-1 ring-orange-DEFAULT/40"
                    : "bg-navy-light/60 text-slate-400 hover:bg-navy-light hover:text-slate-200"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Charts */}
      {error ? (
        <p className="text-sm text-red-300">{error}</p>
      ) : loading ? (
        <div className="flex h-[320px] items-center justify-center">
          <p className="text-sm text-slate-400">Loading profile…</p>
        </div>
      ) : profile?.available ? (
        <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs text-slate-400">
                {profile.month_label ?? MONTH_NAMES[month - 1]} {year} · {profile.type_label ?? (dayType === "ouvre" ? "Workday" : "Weekend / Holiday")} ·
                {" "}Scenario focus: {SCENARIO_OPTIONS.find((option) => option.key === scenario)?.label} ·
                {" "}{P_LEVEL_OPTIONS.find((o) => o.key === pLevel)?.desc}
              </p>
            </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                Projected curves
              </p>
              <ProjectedScenarioCurvesChart data={profile.rows} pLevel={pLevel} />
              <p className="mt-2 text-xs text-slate-500">
                Historical median is shown where the source ENTSO-E day-ahead base file is available. Scenario curves use the selected percentile across Base, High, and Low trajectories.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                Monte Carlo intervals
              </p>
              <MonteCarloIntervalsChart data={profile.rows} scenario={scenario} />
              <p className="mt-2 text-xs text-slate-500">
                Outer band shows P10-P90 and inner band shows P25-P75 for the selected scenario.
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
              Negative-price probability by hour
            </p>
            <NegativeProbabilityChart data={profile.rows} scenario={scenario} />
            <p className="mt-2 text-xs text-slate-500">
              This shows the modeled probability of negative prices by hour for the selected scenario and profile type.
            </p>
          </div>
        </div>
      ) : profile && !profile.available ? (
        <p className="text-sm text-amber-300">
          No profile data available for this combination.
          {(profile as { error?: string }).error ? ` ${(profile as { error?: string }).error}` : ""}
        </p>
      ) : null}
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PriceForecastPage() {
  const { sites } = useSites();
  const [siteId, setSiteId] = useState("");
  const [scenario, setScenario] = useState("base");
  const [startYear, setStartYear] = useState("2027");
  const [endYear, setEndYear] = useState("2046");
  const [baseload, setBaseload] = useState("70");
  const [result, setResult] = useState<PriceForecastResult | null>(null);
  const [siteContext, setSiteContext] = useState<MarketSiteContext | null>(null);
  const [siteContextLoading, setSiteContextLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!siteId) {
      setSiteContext(null);
      return;
    }

    let cancelled = false;
    setSiteContextLoading(true);
    api.market
      .siteContext(siteId)
      .then((response) => {
        if (!cancelled) setSiteContext(response);
      })
      .catch(() => {
        if (!cancelled) setSiteContext(null);
      })
      .finally(() => {
        if (!cancelled) setSiteContextLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  async function runForecast() {
    setLoading(true);
    setError(null);
    try {
      const selectedSite = sites.find((item) => item.id === siteId);
      const response = await api.market.priceForecast({
        site_id: siteId || null,
        site_name: selectedSite?.display_name ?? null,
        annual_production_mwh: selectedSite?.expected_aep_gwh ? selectedSite.expected_aep_gwh * 1000 : null,
        scenario,
        start_year: Number(startYear),
        end_year: Number(endYear),
        baseload_start_eur_mwh: Number(baseload),
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run price forecast.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/long-term-hero.jpg" alt="Price forecast background" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(105deg,rgba(2,18,28,0.94),rgba(5,30,45,0.82),rgba(8,40,54,0.66))]" />
      </div>
      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label="Back to dashboard" />

        <section className="rounded-[30px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">REVEAL market intelligence</p>
          <h1 className="font-dolfines mt-3 text-3xl font-semibold tracking-[0.08em] text-white">Electricity Price Prediction</h1>
          <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-200/84">
            Projects annual spot-price conditions, solar capture-price pressure, and negative-hour risk across a multi-decade horizon. Use the expanded day-ahead profile browser below to compare scenario curves, uncertainty bands, and negative-price exposure by hour.
          </p>
        </section>

        {/* ── Forecast workspace ── */}
        <section className="grid gap-4 lg:grid-cols-[0.75fr_1.25fr]">
          <div className="space-y-4 rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Annual outlook</p>
            <label className="block space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Site</span>
              <select className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100" value={siteId} onChange={(e) => setSiteId(e.target.value)}>
                <option value="">Portfolio-level forecast</option>
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>{site.display_name}</option>
                ))}
              </select>
            </label>
            {siteId ? (
              <div className={`rounded-2xl border p-3 text-sm ${
                siteContext?.has_long_term_output
                  ? "border-emerald-300/20 bg-emerald-500/8 text-emerald-100"
                  : "border-amber-300/20 bg-amber-500/8 text-amber-100"
              }`}>
                {siteContextLoading ? (
                  <p>Checking long-term correlation availability for this site…</p>
                ) : siteContext?.has_long_term_output ? (
                  <div className="space-y-1">
                    <p className="font-semibold">Long-term correlation available</p>
                    <p className="text-xs text-emerald-100/80">{siteContext.recommendation}</p>
                    {siteContext.latest_output_file ? (
                      <p className="text-xs text-emerald-100/70">Latest output: {siteContext.latest_output_file}</p>
                    ) : null}
                    {siteContext.average_annual_energy_mwh ? (
                      <p className="text-xs text-emerald-100/70">Average annual energy: {siteContext.average_annual_energy_mwh.toLocaleString()} MWh</p>
                    ) : null}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="font-semibold">Long-term correlation not available yet</p>
                    <p className="text-xs text-amber-100/80">
                      {siteContext?.recommendation ?? "Run the long-term modelling workflow first so the price forecast can reference the site-specific production basis."}
                    </p>
                    <Link
                      href={`/dashboard/site/${siteId}/long-term-modelling`}
                      className="inline-flex rounded-lg border border-amber-200/20 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-50 transition hover:bg-amber-500/18"
                    >
                      Open long-term modelling
                    </Link>
                  </div>
                )}
              </div>
            ) : null}
            <label className="block space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Scenario</span>
              <select className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100" value={scenario} onChange={(e) => setScenario(e.target.value)}>
                <option value="base">Base (+0.5%/yr)</option>
                <option value="high">High (+1.5%/yr)</option>
                <option value="low">Low (−1.5%/yr)</option>
              </select>
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Start year</span>
                <input className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100" value={startYear} onChange={(e) => setStartYear(e.target.value)} />
              </label>
              <label className="block space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">End year</span>
                <input className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100" value={endYear} onChange={(e) => setEndYear(e.target.value)} />
              </label>
            </div>
            <label className="block space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Starting baseload price (EUR/MWh)</span>
              <input className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100" value={baseload} onChange={(e) => setBaseload(e.target.value)} />
            </label>
            <Button variant="primary" size="lg" className="w-full" loading={loading} onClick={runForecast}>
              Run annual forecast
            </Button>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}

            {result ? (
              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">First year avg</p>
                  <p className="mt-1 text-sm font-semibold text-white">{result.rows[0]?.avg_price_eur_mwh.toFixed(1)}</p>
                  <p className="text-[10px] text-slate-400">EUR/MWh</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Last year avg</p>
                  <p className="mt-1 text-sm font-semibold text-white">{result.rows.at(-1)?.avg_price_eur_mwh.toFixed(1)}</p>
                  <p className="text-[10px] text-slate-400">EUR/MWh</p>
                </div>
                <div className="rounded-2xl border border-red-300/20 bg-red-500/8 p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-red-300">Neg-hr risk</p>
                  <p className="mt-1 text-sm font-semibold text-white">{((result.rows.at(-1)?.negative_hours_pct ?? 0) * 100).toFixed(1)}%</p>
                  <p className="text-[10px] text-slate-400">{result.rows.at(-1)?.negative_hours_estimate} h/yr</p>
                </div>
              </div>
            ) : null}
            {result?.site_profile_basis && siteId ? (
              <p className="text-xs text-slate-400">
                Site basis: {result.site_profile_basis === "site-long-term" ? "long-term correlated production profile" : "configured site production basis"}.
              </p>
            ) : null}
          </div>

          <div className="space-y-4">
            <HourlyProfileSection />

            <div className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">
              {!result ? (
                <p className="text-sm leading-7 text-slate-300/82">
                  Run the annual model to see the multi-year price trajectory, negative-hour counts, and PV cannibalization and BESS relief indices. Results feed into the Performance negative-energy analysis and the Retrofit BESS calculator.
                </p>
              ) : (
                <div className="space-y-6">
                  <PriceTrajectoryChart rows={result.rows} />
                  <p className="-mt-3 text-xs leading-6 text-slate-400">
                    Market average follows the original consultancy day-ahead projection shape and is rescaled so the first forecast year matches your chosen starting baseload. Solar capture price applies a production-shape capture ratio on top of that market curve, using either the site long-term correlation or REVEAL&apos;s generic solar production profile.
                  </p>
                  <div className="h-px bg-white/8" />
                  <NegativeHoursChart rows={result.rows} />
                  <div className="h-px bg-white/8" />
                  <MarketIndicesChart rows={result.rows} />
                  <p className="-mt-3 text-xs leading-6 text-slate-400">
                    `PV cannibalization index` is calculated as `(market average - solar capture price) / market average`, so higher values mean a larger solar discount versus the market. `BESS relief index` is calculated as `(peak negative-hours share - current negative-hours share) / peak negative-hours share`, so higher values mean the projected market has moved further away from the worst negative-price year in the original consultancy trajectory.
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
