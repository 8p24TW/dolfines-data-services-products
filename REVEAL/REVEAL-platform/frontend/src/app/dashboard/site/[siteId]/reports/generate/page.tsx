"use client";

import Image from "next/image";
import { Suspense, useState, useCallback, useMemo, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSite } from "@/hooks/useSites";
import { useAnalysisRun, useColumnDetect } from "@/hooks/useAnalysis";
import { ColumnMapper } from "@/components/reports/ColumnMapper";
import { ReportProgress } from "@/components/reports/ReportProgress";
import { WaterfallChart } from "@/components/charts/WaterfallChart";
import { Button } from "@/components/ui/Button";
import { BackLink } from "@/components/layout/BackLink";
import { api } from "@/lib/api";
import { savePerformancePreviewSnapshot } from "@/lib/performance-preview";
import type { ReportType } from "@/types/report";
import type { AnalysisColumnMapping, AnalysisResult, ColumnDetectionResult } from "@/types/analysis";
import { useTranslation } from "@/lib/i18n";

const ANALYSIS_OPTIONS: Array<{
  type: ReportType;
  stepLabel: string;
  title: string;
  description: string;
  accent: string;
}> = [
  {
    type: "daily",
    stepLabel: "Quick check",
    title: "Daily / short-period screening",
    description: "Best for daily files or short periods where the goal is to validate data quality, inverter availability, and headline KPIs quickly.",
    accent: "from-sky-400/95 to-sky-600/70",
  },
  {
    type: "monthly",
    stepLabel: "Summary review",
    title: "Monthly / aggregated review",
    description: "Best for aggregated monthly data where the priority is trend context, plant-level performance, and specific-yield benchmarking.",
    accent: "from-emerald-400/95 to-emerald-600/70",
  },
  {
    type: "comprehensive",
    stepLabel: "Comprehensive diagnosis",
    title: "6+ month operational diagnosis",
    description: "Best for rich SCADA periods where REVEAL should diagnose PR, availability, recoverable losses, and the main improvement points.",
    accent: "from-violet-400/95 to-violet-600/70",
  },
];

function formatDateRange(range?: [string, string] | null) {
  if (!range?.[0] || !range?.[1]) return "Date range will appear once REVEAL has analysed the upload.";
  return `${range[0]} to ${range[1]}`;
}

function average(values: number[]) {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function parseDateValue(value?: string | null) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getObservedDays(range?: [string, string] | null, fallbackMonths: string[] = []) {
  const start = parseDateValue(range?.[0]);
  const end = parseDateValue(range?.[1]);
  if (start && end) {
    const elapsedDays = (end.getTime() - start.getTime()) / 86_400_000;
    if (elapsedDays > 0) return elapsedDays;
  }

  if (fallbackMonths.length > 0) {
    return fallbackMonths.length * (365.25 / 12);
  }

  return 365.25;
}

function formatMonthLabel(month: string) {
  const [year, monthPart] = month.split("-");
  if (!year || !monthPart) return month;
  return `${monthPart}/${year.slice(-2)}`;
}

function maxOf(values: number[]) {
  return values.length ? Math.max(...values) : 0;
}

function selectAllOnFocus(event: React.FocusEvent<HTMLInputElement>) {
  event.currentTarget.select();
}

function parseMonthValue(value: string) {
  if (!value) return null;
  const date = new Date(`${value}-01T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatMonthValue(date: Date) {
  return `${date.getFullYear()}-${`${date.getMonth() + 1}`.padStart(2, "0")}`;
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, delta: number) {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1);
}

function isMonthDisabled(date: Date, min?: string, max?: string) {
  const value = formatMonthValue(date);
  if (min && value < min) return true;
  if (max && value > max) return true;
  return false;
}

function MonthFieldPicker({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
}) {
  const selectedMonth = useMemo(() => parseMonthValue(value), [value]);
  const [open, setOpen] = useState(false);
  const [visibleYear, setVisibleYear] = useState<number>(() => (selectedMonth ?? parseMonthValue(min ?? "") ?? new Date()).getFullYear());
  const months = Array.from({ length: 12 }, (_, index) => new Date(visibleYear, index, 1));

  useEffect(() => {
    if (selectedMonth) {
      setVisibleYear(selectedMonth.getFullYear());
    }
  }, [selectedMonth]);

  return (
    <div className="relative min-w-[180px] flex-1">
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/45">{label}</p>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="mt-2 flex h-10 w-full items-center rounded-xl border border-white/12 bg-[rgba(255,255,255,0.06)] px-3 text-left text-sm font-medium text-white transition hover:border-white/24"
      >
        {value ? formatMonthLabel(value) : `Select ${label.toLowerCase()}`}
      </button>
      {open ? (
        <div className="absolute left-0 top-[calc(100%+0.5rem)] z-30 w-[18rem] rounded-2xl border border-white/12 bg-[rgba(4,18,30,0.98)] p-3 shadow-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setVisibleYear((current) => current - 1)}
              className="rounded-lg border border-white/12 bg-white/5 px-2.5 py-1.5 text-sm text-white transition hover:border-white/24"
            >
              Prev
            </button>
            <p className="text-sm font-semibold text-white">{visibleYear}</p>
            <button
              type="button"
              onClick={() => setVisibleYear((current) => current + 1)}
              className="rounded-lg border border-white/12 bg-white/5 px-2.5 py-1.5 text-sm text-white transition hover:border-white/24"
            >
              Next
            </button>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {months.map((monthDate) => {
              const monthValue = formatMonthValue(monthDate);
              const disabled = isMonthDisabled(monthDate, min, max);
              const selected = value === monthValue;
              return (
                <button
                  key={monthValue}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    onChange(monthValue);
                    setOpen(false);
                  }}
                  className={`rounded-lg px-3 py-2 text-sm transition ${
                    selected
                      ? "bg-orange-500 text-white"
                      : disabled
                        ? "cursor-not-allowed text-white/20"
                        : "bg-white/5 text-white hover:bg-white/8"
                  }`}
                >
                  {monthDate.toLocaleDateString("en-GB", { month: "short" })}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function normalizeDecimalInput(value: string) {
  return value.replace(/,/g, ".");
}

function buildExecutiveSummary(result: AnalysisResult | null) {
  if (!result) return [];

  const topIssues = result.punchlist.slice(0, 3).map((item) => item.finding);
  const annualPr = result.pr.annual.at(-1)?.PR_pct ?? average(result.pr.monthly.map((item) => item.PR_pct));
  const totalEnergyMwh = result.pr.monthly.reduce((sum, item) => sum + item.E_act_mwh, 0);
  const observedDays = getObservedDays(result.summary.data_date_range, result.pr.monthly.map((item) => item.month));
  const annualisedSiteYield =
    result.summary.cap_dc_kwp > 0 && observedDays > 0
      ? (totalEnergyMwh * 1000 * (365.25 / observedDays)) / result.summary.cap_dc_kwp
      : 0;
  const highPriorityCount = result.punchlist.filter((item) => item.priority === "HIGH").length;

  return [
    `REVEAL analysed ${result.summary.n_inverters} inverter(s) across ${formatDateRange(result.summary.data_date_range)} with ${result.data_quality.overall_power_pct.toFixed(1)}% power-data completeness and ${result.data_quality.irradiance_pct.toFixed(1)}% irradiance-data completeness.`,
    `Fleet mean availability is ${result.availability.mean_pct.toFixed(1)}% and the latest annual PR is ${annualPr.toFixed(1)}%. Annualised whole-site specific yield sits at ${annualisedSiteYield.toFixed(1)} kWh/kWp/yr.`,
    highPriorityCount > 0
      ? `REVEAL has flagged ${highPriorityCount} high-priority improvement point${highPriorityCount === 1 ? "" : "s"} for follow-up.`
      : "REVEAL did not identify any high-priority improvement points in the current dataset.",
    topIssues.length > 0 ? `Main issues detected: ${topIssues.join(" • ")}.` : "No punchlist findings are available yet for this dataset.",
  ];
}

function getHeatTileClass(quality: { completenessPct: number; missingPct: number; frozenPct: number }) {
  if (quality.frozenPct > 0 && quality.missingPct > 0) {
    return "border-red-300/70 bg-[linear-gradient(135deg,rgba(220,38,38,0.5)_0%,rgba(220,38,38,0.5)_49%,rgba(244,114,182,0.28)_51%,rgba(244,114,182,0.28)_100%)] text-white shadow-[inset_0_0_0_1px_rgba(248,113,113,0.22)]";
  }
  if (quality.frozenPct > 0) return "border-red-300/70 bg-red-600/40 text-white shadow-[inset_0_0_0_1px_rgba(248,113,113,0.22)]";
  if (quality.completenessPct >= 95) return "border-emerald-300/25 bg-emerald-400/15 text-emerald-50";
  if (quality.missingPct > 0) return "border-rose-300/35 bg-rose-400/20 text-rose-50";
  if (quality.completenessPct >= 85) return "border-sky-300/25 bg-sky-400/18 text-sky-50";
  return "border-white/15 bg-white/8 text-slate-100";
}

function getRainHeatTileStyle(totalRainMm: number) {
  if (!Number.isFinite(totalRainMm) || totalRainMm <= 0) {
    return {
      borderColor: "rgba(255,255,255,0.12)",
      background: "rgba(255,255,255,0.05)",
      color: "#e2e8f0",
    };
  }
  if (totalRainMm >= 120) {
    return {
      borderColor: "rgba(255,255,255,0.72)",
      background: "rgba(255,255,255,0.88)",
      color: "#0f172a",
    };
  }
  if (totalRainMm >= 60) {
    return {
      borderColor: "rgba(255,245,245,0.72)",
      background: "rgba(255,226,226,0.85)",
      color: "#7f1d1d",
    };
  }
  if (totalRainMm >= 25) {
    return {
      borderColor: "rgba(252,165,165,0.65)",
      background: "rgba(220,38,38,0.55)",
      color: "#fff7f7",
    };
  }
  if (totalRainMm >= 5) {
    return {
      borderColor: "rgba(248,113,113,0.45)",
      background: "rgba(239,68,68,0.22)",
      color: "#ffe4e6",
    };
  }
  return {
    borderColor: "rgba(252,165,165,0.35)",
    background: "rgba(248,113,113,0.12)",
    color: "#fecdd3",
  };
}

function WorkflowPanel({
  step,
  title,
  description,
  accent,
  summary,
  active,
  completed,
  collapsed,
  activeTone = "default",
  onToggle,
  children,
}: {
  step: string;
  title: string;
  description: string;
  accent: string;
  summary: string;
  active: boolean;
  completed: boolean;
  collapsed: boolean;
  activeTone?: "default" | "dark";
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-[28px] border p-5 backdrop-blur-sm transition-all duration-300 ${
        active
          ? activeTone === "dark"
            ? "border-white/40 bg-[linear-gradient(135deg,rgba(4,18,30,0.94),rgba(6,24,38,0.9))] shadow-[0_0_0_1px_rgba(255,255,255,0.12),0_0_28px_rgba(96,165,250,0.08)] animate-[workflowPulse_2.6s_ease-in-out_infinite]"
            : "border-white/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.12),rgba(255,255,255,0.04))] shadow-[0_0_0_1px_rgba(255,255,255,0.2),0_0_32px_rgba(120,197,255,0.14)] animate-[workflowPulse_2.6s_ease-in-out_infinite]"
          : "border-white/14 bg-[rgba(3,16,26,0.76)]"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className={`h-1.5 w-28 rounded-full bg-gradient-to-r ${accent}`} />
          <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/52">{step}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h2 className="font-dolfines text-[1.8rem] font-semibold tracking-[0.04em] text-white">{title}</h2>
            {completed ? (
              <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-100">
                Ready
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm leading-7 text-slate-200/84">{description}</p>
          <p className="mt-4 text-xs leading-6 text-white/55">{summary}</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-white/20 bg-white/6 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/82 transition hover:border-white/35 hover:text-white"
        >
          {collapsed ? "Expand details" : "Collapse details"}
        </button>
      </div>
      {!collapsed ? <div className="mt-6">{children}</div> : null}
    </section>
  );
}

function MetricBars({
  title,
  description,
  rows,
  colorClass,
  valueSuffix = "",
}: {
  title: string;
  description: string;
  rows: Array<{ label: string; value: number; secondary?: string }>;
  colorClass: string;
  valueSuffix?: string;
}) {
  const maxValue = maxOf(rows.map((row) => row.value));
  return (
    <div className="rounded-[24px] border border-white/10 bg-[rgba(4,18,30,0.88)] p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">{title}</p>
      <p className="mt-2 text-sm leading-7 text-slate-200/82">{description}</p>
      <div className="mt-5 space-y-3">
        {rows.map((row) => {
          const width = maxValue > 0 ? `${Math.max((row.value / maxValue) * 100, 6)}%` : "6%";
          return (
            <div key={row.label} className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-sm text-white">
                <span className="font-semibold">{row.label}</span>
                <span className="text-right font-semibold">
                  {row.value.toFixed(1)}
                  {valueSuffix}
                </span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
                <div className={`h-full rounded-full ${colorClass}`} style={{ width }} />
              </div>
              {row.secondary ? <p className="mt-2 text-xs leading-6 text-white/55">{row.secondary}</p> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChartShell({
  title,
  description,
  children,
  heightClass = "h-[320px]",
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  heightClass?: string;
}) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-[rgba(4,18,30,0.88)] p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">{title}</p>
      <p className="mt-2 text-sm leading-7 text-slate-200/82">{description}</p>
      <div className={`mt-5 ${heightClass}`}>{children}</div>
    </div>
  );
}

function AnalysisSection({
  id,
  title,
  description,
  collapsed,
  onToggle,
  children,
}: {
  id: string;
  title: string;
  description: string;
  collapsed: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[26px] border border-white/10 bg-[rgba(4,18,30,0.88)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">{id}</p>
          <h3 className="mt-2 font-dolfines text-[1.45rem] font-semibold tracking-[0.04em] text-white">{title}</h3>
          <p className="mt-2 text-sm leading-7 text-slate-200/82">{description}</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-white/20 bg-white/6 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/82 transition hover:border-white/35 hover:text-white"
        >
          {collapsed ? "Expand section" : "Collapse section"}
        </button>
      </div>
      {!collapsed ? <div className="mt-5">{children}</div> : null}
    </section>
  );
}

function RevealTooltip({
  active,
  payload,
  label,
  labelFormatter,
  valueSuffix = "",
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; color?: string }>;
  label?: string;
  labelFormatter?: (label: string) => string;
  valueSuffix?: string;
}) {
  if (!active || !payload?.length) return null;
  const resolvedLabel = labelFormatter ? labelFormatter(label ?? "") : label;
  return (
    <div className="rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.94)] px-4 py-3 shadow-[0_14px_28px_rgba(0,0,0,0.35)]">
      {resolvedLabel ? <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/70">{resolvedLabel}</p> : null}
      <div className="mt-2 space-y-2">
        {payload.map((entry, index) => (
          <div key={`${entry.name}-${index}`} className="flex items-center justify-between gap-4 text-sm">
            <span className="text-white/72">{entry.name}</span>
            <span className="font-semibold text-white">
              {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}
              {typeof entry.value === "number" ? valueSuffix : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function GenerateReportPageContent({ params }: { params: { siteId: string } }) {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const reportType = (searchParams.get("type") ?? "comprehensive") as ReportType;
  const { site } = useSite(params.siteId);
  const { trigger: detectColumns, isMutating: isDetecting } = useColumnDetect();
  const { trigger: runAnalysis, isMutating: isRunningAnalysis } = useAnalysisRun();

  const [files, setFiles] = useState<File[]>([]);
  const [lang, setLang] = useState<"en" | "fr" | "de">("en");
  const [reportDate, setReportDate] = useState("");
  const [columnMappings, setColumnMappings] = useState<Record<string, AnalysisColumnMapping>>({});
  const [detectedMappings, setDetectedMappings] = useState<Record<string, ColumnDetectionResult>>({});
  const [detectionError, setDetectionError] = useState<string | null>(null);
  const [worksheetLoadingFile, setWorksheetLoadingFile] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisSignature, setAnalysisSignature] = useState<string | null>(null);
  const [analysisRequested, setAnalysisRequested] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [detectionProgress, setDetectionProgress] = useState(0);
  const [detectionProgressLabel, setDetectionProgressLabel] = useState("");
  const [previewProgress, setPreviewProgress] = useState(0);
  const [previewProgressLabel, setPreviewProgressLabel] = useState("");
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisProgressLabel, setAnalysisProgressLabel] = useState("");
  const [assumptionsConfirmed, setAssumptionsConfirmed] = useState(false);
  const [analysisLaunched, setAnalysisLaunched] = useState(false);
  const [dataConfirmed, setDataConfirmed] = useState(false);
  const [analysisChosen, setAnalysisChosen] = useState(false);
  const [languageChosen, setLanguageChosen] = useState(false);
  const [inverterType, setInverterType] = useState("");
  const [inverterQuantity, setInverterQuantity] = useState("");
  const [moduleQuantity, setModuleQuantity] = useState("");
  const [moduleCapacityWp, setModuleCapacityWp] = useState("");
  const [moduleTiltDeg, setModuleTiltDeg] = useState("");
  const [siteTariffEurMwh, setSiteTariffEurMwh] = useState("");
  const [irradianceBasis, setIrradianceBasis] = useState<"poa" | "ghi">("poa");
  const [waterfallStartMonthDraft, setWaterfallStartMonthDraft] = useState("");
  const [waterfallEndMonthDraft, setWaterfallEndMonthDraft] = useState("");
  const [waterfallStartMonth, setWaterfallStartMonth] = useState("");
  const [waterfallEndMonth, setWaterfallEndMonth] = useState("");
  const [collapsedSteps, setCollapsedSteps] = useState<Record<number, boolean>>({
    1: false,
    2: false,
    3: false,
    4: false,
  });
  const [collapsedAnalysisSections, setCollapsedAnalysisSections] = useState<Record<string, boolean>>({
    overview: true,
    weather: true,
    availability: true,
    site: true,
    inverter: true,
    losses: true,
    actions: true,
    export: true,
  });

  const currentAnalysis = ANALYSIS_OPTIONS.find((option) => option.type === reportType) ?? ANALYSIS_OPTIONS[2];
  const filesReadyForReview =
    files.length > 0 && !isDetecting && !worksheetLoadingFile && files.every((file) => Boolean(detectedMappings[file.name]));

  const detectionList = useMemo(
    () => files.map((file) => ({ file, detection: detectedMappings[file.name] })).filter((item) => Boolean(item.detection)),
    [files, detectedMappings]
  );

  const totalRows = detectionList.reduce((sum, item) => sum + (item.detection?.row_count ?? 0), 0);
  const powerColumnsSelected = detectionList.reduce((sum, item) => sum + (item.detection?.mapping.power?.length ?? 0), 0);
  const firstRange = detectionList[0]?.detection?.data_date_range;
  const previewSignature = useMemo(
    () =>
      JSON.stringify({
        reportType,
        files: files.map((file) => ({ name: file.name, size: file.size, lastModified: file.lastModified })),
        mappings: columnMappings,
      }),
    [columnMappings, files, reportType]
  );
  const executiveSummary = useMemo(() => buildExecutiveSummary(analysisResult), [analysisResult]);
  const totalEnergyMwh = useMemo(
    () => (analysisResult ? analysisResult.pr.monthly.reduce((sum, item) => sum + item.E_act_mwh, 0) : 0),
    [analysisResult]
  );
  const annualisedSiteSpecificYield = useMemo(() => {
    if (!analysisResult) return 0;
    const observedDays = getObservedDays(analysisResult.summary.data_date_range, analysisResult.pr.monthly.map((item) => item.month));
    if (analysisResult.summary.cap_dc_kwp <= 0 || observedDays <= 0) return 0;
    return (totalEnergyMwh * 1000 * (365.25 / observedDays)) / analysisResult.summary.cap_dc_kwp;
  }, [analysisResult, totalEnergyMwh]);
  const tariffEurMwh = useMemo(() => {
    const numeric = Number(siteTariffEurMwh);
    return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
  }, [siteTariffEurMwh]);
  const inferredAcCapacityKw = useMemo(() => {
    if (!site) return 0;
    const siteWithAc = site as typeof site & { cap_ac_kw?: number };
    const baseAcKw = siteWithAc.cap_ac_kw ?? 0;
    const perInverterKw = site.n_inverters && site.n_inverters > 0 ? baseAcKw / site.n_inverters : 0;
    const selectedInverters = Number(inverterQuantity);
    if (Number.isFinite(selectedInverters) && selectedInverters > 0 && perInverterKw > 0) {
      return selectedInverters * perInverterKw;
    }
    return baseAcKw;
  }, [inverterQuantity, site]);
  const dcAcRatio = useMemo(() => {
    if (!site || inferredAcCapacityKw <= 0) return null;
    return site.cap_dc_kwp / inferredAcCapacityKw;
  }, [inferredAcCapacityKw, site]);
  const latestAnnualPr = useMemo(
    () =>
      analysisResult
        ? (analysisResult.pr.annual.at(-1)?.PR_pct ?? average(analysisResult.pr.monthly.map((item) => item.PR_pct)))
        : 0,
    [analysisResult]
  );
  const heatMapMonths = useMemo(() => {
    if (!analysisResult) return [];
    return Array.from(new Set(analysisResult.data_quality.monthly.map((item) => item.month))).sort();
  }, [analysisResult]);
  const heatMapInverters = useMemo(() => {
    if (!analysisResult) return [];
    return Array.from(new Set(analysisResult.data_quality.monthly.map((item) => item.inv_id))).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }, [analysisResult]);
  const heatMapLookup = useMemo(() => {
    const lookup = new Map<string, { completenessPct: number; missingPct: number; frozenPct: number }>();
    if (!analysisResult) return lookup;
    for (const item of analysisResult.data_quality.monthly) {
      lookup.set(`${item.month}::${item.inv_id}`, {
        completenessPct: item.completeness_pct,
        missingPct: item.missing_pct,
        frozenPct: item.frozen_pct,
      });
    }
    return lookup;
  }, [analysisResult]);
  const topPunchlist = useMemo(() => analysisResult?.punchlist.slice(0, 6) ?? [], [analysisResult]);
  const latestMonths = useMemo(() => (analysisResult ? analysisResult.pr.monthly : []), [analysisResult]);
  const latestAvailabilityMonths = useMemo(() => (analysisResult ? analysisResult.availability.site_monthly : []), [analysisResult]);
  const analysisMonths = useMemo(() => latestMonths.map((item) => item.month), [latestMonths]);
  const effectiveWaterfallStartMonth = waterfallStartMonth || analysisMonths[0] || "";
  const effectiveWaterfallEndMonth = waterfallEndMonth || analysisMonths[analysisMonths.length - 1] || "";
  const filteredWaterfallMonths = useMemo(() => {
    if (!latestMonths.length) return [];
    return latestMonths.filter(
      (item) =>
        (!effectiveWaterfallStartMonth || item.month >= effectiveWaterfallStartMonth) &&
        (!effectiveWaterfallEndMonth || item.month <= effectiveWaterfallEndMonth)
    );
  }, [effectiveWaterfallEndMonth, effectiveWaterfallStartMonth, latestMonths]);
  const filteredWaterfallContext = useMemo(() => {
    if (!analysisResult || !latestMonths.length || !filteredWaterfallMonths.length) {
      return {
        chartData: analysisResult?.waterfall ?? [],
        designYieldMwh: analysisResult?.diagnosis.summary.design_yield_mwh ?? 0,
        weatherCorrectedYieldMwh: analysisResult?.diagnosis.summary.weather_corrected_yield_mwh ?? 0,
        recoverableMwh: analysisResult?.diagnosis.summary.recoverable_mwh ?? 0,
        overUnderPerformanceMwh: analysisResult?.diagnosis.summary.over_under_performance_mwh ?? 0,
        actualYieldMwh: analysisResult?.diagnosis.summary.actual_yield_mwh ?? 0,
      };
    }

    const totalActual = latestMonths.reduce((sum, item) => sum + item.E_act_mwh, 0);
    const totalReference = latestMonths.reduce((sum, item) => sum + item.E_ref_mwh, 0);
    const selectedActual = filteredWaterfallMonths.reduce((sum, item) => sum + item.E_act_mwh, 0);
    const selectedReference = filteredWaterfallMonths.reduce((sum, item) => sum + item.E_ref_mwh, 0);
    const actualShare = totalActual > 0 ? selectedActual / totalActual : 1;
    const referenceShare = totalReference > 0 ? selectedReference / totalReference : actualShare;
    const summary = analysisResult.diagnosis.summary;
    const scaledDesignYield = summary.design_yield_mwh * referenceShare;
    const scaledWeatherCorrectedYield = summary.weather_corrected_yield_mwh * referenceShare;
    const scaledRecoverable = summary.recoverable_mwh * actualShare;
    const scaledOverUnder = summary.over_under_performance_mwh * actualShare;
    const scaledActual = summary.actual_yield_mwh * actualShare;

    const chartData = analysisResult.waterfall.map((item) => {
      if (item.label === "Design yield") return { ...item, value_mwh: scaledDesignYield };
      if (item.label === "Weather-corrected yield") return { ...item, value_mwh: scaledWeatherCorrectedYield };
      if (item.label === "Actual yield") return { ...item, value_mwh: scaledActual };
      if (item.label === "Over / under performance") return { ...item, value_mwh: scaledOverUnder };
      if (item.type === "loss") {
        const lower = item.label.toLowerCase();
        const usesReferenceShare = lower.includes("irradiance") || lower.includes("temperature");
        return { ...item, value_mwh: Math.abs(item.value_mwh) * (usesReferenceShare ? referenceShare : actualShare) };
      }
      return item;
    });

    return {
      chartData,
      designYieldMwh: scaledDesignYield,
      weatherCorrectedYieldMwh: scaledWeatherCorrectedYield,
      recoverableMwh: scaledRecoverable,
      overUnderPerformanceMwh: scaledOverUnder,
      actualYieldMwh: scaledActual,
    };
  }, [analysisResult, filteredWaterfallMonths, latestMonths]);
  const yieldRanking = useMemo(() => {
    if (!analysisResult) return [];
    const sorted = [...analysisResult.specific_yield];
    if (sorted.length <= 4) return sorted;
    const combined = [...sorted.slice(0, 2), ...sorted.slice(-2)];
    const unique = new Map(combined.map((item) => [item.inv_id, item]));
    return Array.from(unique.values());
  }, [analysisResult]);
  const mttfRanking = useMemo(
    () => (analysisResult ? [...analysisResult.mttf.by_inverter].sort((a, b) => a.mttf_hours - b.mttf_hours).slice(0, 8) : []),
    [analysisResult]
  );
  const startStopOutliers = useMemo(
    () =>
      analysisResult
        ? [...analysisResult.start_stop]
            .sort((a, b) => Math.abs(b.start_dev) - Math.abs(a.start_dev))
            .slice(0, 8)
        : [],
    [analysisResult]
  );
  const peerGroupRows = useMemo(() => analysisResult?.peer_groups ?? [], [analysisResult]);
  const clippingBins = useMemo(() => analysisResult?.clipping.by_irradiance_bin ?? [], [analysisResult]);
  const clippingInverters = useMemo(() => analysisResult?.clipping.top_inverters ?? [], [analysisResult]);
  const lossBreakdown = useMemo(() => analysisResult?.diagnosis.loss_breakdown ?? [], [analysisResult]);
  const curtailmentCandidates = useMemo(() => analysisResult?.diagnosis.curtailment_candidates ?? [], [analysisResult]);
  const diagnosisCommentary = useMemo(() => analysisResult?.diagnosis.commentary ?? [], [analysisResult]);
  const rootCauses = useMemo(() => analysisResult?.diagnosis.root_causes ?? [], [analysisResult]);
  const degradationTrendRows = useMemo(
    () => (analysisResult ? analysisResult.pr.annual.map((item) => ({ year: String(item.year), pr_pct: item.PR_pct, energy_mwh: item.E_act_mwh })) : []),
    [analysisResult]
  );
  const weatherMonthlyRows = useMemo(() => analysisResult?.weather.monthly ?? [], [analysisResult]);
  const weatherSummary = useMemo(() => analysisResult?.weather.summary ?? null, [analysisResult]);
  const weatherEvents = useMemo(() => analysisResult?.weather.events ?? [], [analysisResult]);
  const monthlyTimelineRows = useMemo(() => {
    if (!analysisResult) return [];
    const qualityByMonth = new Map(
      analysisResult.data_quality.monthly.reduce<Array<[string, { missingPct: number; frozenPct: number }]>>((acc, item) => {
        const current = acc.find(([month]) => month === item.month)?.[1];
        if (current) {
          current.missingPct = Math.max(current.missingPct, item.missing_pct);
          current.frozenPct = Math.max(current.frozenPct, item.frozen_pct);
        } else {
          acc.push([item.month, { missingPct: item.missing_pct, frozenPct: item.frozen_pct }]);
        }
        return acc;
      }, [])
    );
    const availabilityByMonth = new Map(analysisResult.availability.site_monthly.map((item) => [item.month, item.avail_pct]));
    const curtailmentByMonth = new Map(analysisResult.diagnosis.curtailment_candidates.map((item) => [item.month, item.loss_mwh]));
    return analysisResult.pr.monthly.map((item) => {
      const quality = qualityByMonth.get(item.month) ?? { missingPct: 0, frozenPct: 0 };
      return {
        month: item.month,
        pr_pct: item.PR_pct,
        irradiation_kwh_m2: item.irrad_kwh_m2,
        energy_mwh: item.E_act_mwh,
        availability_pct: availabilityByMonth.get(item.month) ?? 0,
        missing_pct: quality.missingPct,
        frozen_pct: quality.frozenPct,
        curtailment_mwh: curtailmentByMonth.get(item.month) ?? 0,
      };
    });
  }, [analysisResult]);
  const dataLimitations = useMemo(() => {
    if (!analysisResult) return [];
    const notes = [
      `Power-data availability is ${analysisResult.data_quality.overall_power_pct.toFixed(1)}% and irradiance availability is ${analysisResult.data_quality.irradiance_pct.toFixed(1)}% over the analysed daytime window.`,
      `REVEAL screened frozen readings from ${analysisResult.data_quality.stuck_inverters_count ?? 0} inverter stream(s) before calculating the diagnosis.`,
      analysisResult.weather.error
        ? `ERA precipitation could not be loaded for this run, so rain-linked soiling checks remain unavailable in the current diagnosis.`
        : `REVEAL has loaded ERA precipitation context for the analysed period. Rain events can now be reviewed in Step 4 to support later excess-soiling interpretation, while full irradiance-reference correlation still lives in the Long-Term workflow.`,
    ];
    if (analysisResult.pr.annual.length < 3) {
      notes.push("Fewer than three annual periods are available, so degradation and long-term performance drift should be interpreted cautiously.");
    }
    return notes;
  }, [analysisResult]);
  const lossActionRows = useMemo(() => {
    if (!analysisResult) return [];
    return analysisResult.diagnosis.loss_breakdown
      .filter((item) => item.value_mwh > 0.01)
      .map((item, index) => {
        const rootCause = rootCauses[index] ?? rootCauses.find((candidate) =>
          candidate.title.toLowerCase().includes(item.label.toLowerCase().split(" ")[0])
        );
        return {
          ...item,
          value_keur: tariffEurMwh > 0 ? (item.value_mwh * tariffEurMwh) / 1000 : 0,
          action:
            rootCause?.action ??
            (item.classification === "recoverable"
              ? "Investigate this recoverable bucket in detail and test it in the digital twin."
              : "Treat this as a baseline or residual bucket unless later evidence shows it is recoverable."),
        };
      });
  }, [analysisResult, rootCauses, tariffEurMwh]);
  const mttfBenchmarkedRows = useMemo(() => {
    if (!analysisResult) return [];
    return analysisResult.mttf.by_inverter
      .map((item) => {
        const status =
          item.mttf_hours >= 1500
            ? "Above industry benchmark"
            : item.mttf_hours >= 750
              ? "Watch list"
              : "Below benchmark";
        return { ...item, status };
      })
      .sort((a, b) => a.mttf_hours - b.mttf_hours);
  }, [analysisResult]);
  const step1Configured = analysisChosen && languageChosen;
  const previewReady = analysisSignature === previewSignature && Boolean(analysisResult) && !isRunningAnalysis;
  const previewSettled = previewReady || Boolean(analysisError);
  const siteDetailsReady =
    inverterType.trim().length > 0 &&
    inverterQuantity.trim().length > 0 &&
    siteTariffEurMwh.trim().length > 0 &&
    (site?.site_type === "wind" ||
      (moduleQuantity.trim().length > 0 && moduleCapacityWp.trim().length > 0 && moduleTiltDeg.trim().length > 0));
  const siteConfigOverrides = useMemo(
    () => ({
      inv_model: inverterType.trim(),
      n_inverters: inverterQuantity ? Number(inverterQuantity) : undefined,
      n_modules: moduleQuantity ? Number(moduleQuantity) : undefined,
      module_wp: moduleCapacityWp ? Number(moduleCapacityWp) : undefined,
      module_tilt_deg: moduleTiltDeg ? Number(moduleTiltDeg) : undefined,
      tariff_eur_mwh: siteTariffEurMwh ? Number(siteTariffEurMwh) : undefined,
      irradiance_basis: irradianceBasis,
    }),
    [inverterQuantity, inverterType, irradianceBasis, moduleCapacityWp, moduleQuantity, moduleTiltDeg, siteTariffEurMwh]
  );

  const activeStep = !step1Configured ? 1 : files.length === 0 || !filesReadyForReview || !dataConfirmed ? 2 : !assumptionsConfirmed || !analysisLaunched ? 3 : 4;

  useEffect(() => {
    setAssumptionsConfirmed(false);
    setAnalysisLaunched(false);
  }, [reportType, files.length, totalRows, dataConfirmed]);

  useEffect(() => {
    if (!site) return;
    setInverterType(site.inv_model ?? "");
    setInverterQuantity(site.n_inverters ? String(site.n_inverters) : "");
    setModuleQuantity(site.n_modules ? String(site.n_modules) : "");
    setModuleCapacityWp(site.module_wp ? String(site.module_wp) : "");
    setSiteTariffEurMwh(((site as { tariff_eur_mwh?: number } | undefined)?.tariff_eur_mwh) ? String((site as { tariff_eur_mwh?: number }).tariff_eur_mwh) : "");
  }, [site]);

  useEffect(() => {
    if (!analysisMonths.length) {
      setWaterfallStartMonth("");
      setWaterfallEndMonth("");
      setWaterfallStartMonthDraft("");
      setWaterfallEndMonthDraft("");
      return;
    }
    setWaterfallStartMonth((current) => current || analysisMonths[0]);
    setWaterfallEndMonth((current) => current || analysisMonths[analysisMonths.length - 1]);
    setWaterfallStartMonthDraft((current) => current || analysisMonths[0]);
    setWaterfallEndMonthDraft((current) => current || analysisMonths[analysisMonths.length - 1]);
  }, [analysisMonths]);

  useEffect(() => {
    setAnalysisResult(null);
    setAnalysisError(null);
    setAnalysisSignature(null);
    setAnalysisRequested(false);
    setAnalysisLaunched(false);
    setDataConfirmed(false);
    setJobId(null);
  }, [previewSignature]);

  useEffect(() => {
    if (!isDetecting) {
      if (detectionProgress > 0) {
        setDetectionProgress(100);
        const resetTimer = window.setTimeout(() => {
          setDetectionProgress(0);
          setDetectionProgressLabel("");
        }, 900);
        return () => window.clearTimeout(resetTimer);
      }
      return;
    }

    if (!detectionProgressLabel) {
      setDetectionProgressLabel("Analysing uploaded file structure");
    }

    const timer = window.setInterval(() => {
      setDetectionProgress((current) => Math.min(current + (current < 60 ? 9 : current < 85 ? 4 : 1), 92));
    }, 220);

    return () => window.clearInterval(timer);
  }, [detectionProgress, detectionProgressLabel, isDetecting]);

  useEffect(() => {
    if (!isRunningAnalysis) {
      if (previewProgress > 0) {
        setPreviewProgress(100);
        const resetTimer = window.setTimeout(() => {
          setPreviewProgress(0);
          setPreviewProgressLabel("");
        }, 900);
        return () => window.clearTimeout(resetTimer);
      }
      return;
    }

    if (!previewProgressLabel) {
      setPreviewProgressLabel("Building the data-quality preview");
    }

    const timer = window.setInterval(() => {
      setPreviewProgress((current) => Math.min(current + (current < 45 ? 8 : current < 78 ? 4 : 1), 94));
    }, 260);

    return () => window.clearInterval(timer);
  }, [isRunningAnalysis, previewProgress, previewProgressLabel]);

  useEffect(() => {
    if (!assumptionsConfirmed) {
      setAnalysisProgress(0);
      setAnalysisProgressLabel("");
      return;
    }
    if (!isRunningAnalysis) {
      if (analysisProgress > 0) {
        setAnalysisProgress(100);
        const resetTimer = window.setTimeout(() => {
          setAnalysisProgress(0);
          setAnalysisProgressLabel("");
        }, 900);
        return () => window.clearTimeout(resetTimer);
      }
      return;
    }

    if (!analysisProgressLabel) {
      setAnalysisProgressLabel("Generating the in-app performance analysis");
    }

    const timer = window.setInterval(() => {
      setAnalysisProgress((current) => Math.min(current + (current < 35 ? 9 : current < 75 ? 4 : 1), 94));
    }, 260);

    return () => window.clearInterval(timer);
  }, [analysisProgress, analysisProgressLabel, assumptionsConfirmed, isRunningAnalysis]);

  useEffect(() => {
    setCollapsedSteps({
      1: activeStep !== 1,
      2: activeStep !== 2,
      3: activeStep !== 3,
      4: activeStep !== 4,
    });
  }, [activeStep]);

  const requestPreview = useCallback(async () => {
    if (!site || !filesReadyForReview || isRunningAnalysis) return;
    try {
      setAnalysisRequested(true);
      setAnalysisError(null);
      if (assumptionsConfirmed) {
        setAnalysisProgress(10);
        setAnalysisProgressLabel("Generating the in-app performance analysis");
      } else {
        setPreviewProgress(10);
        setPreviewProgressLabel("Preparing the heat-map preview");
      }
      const result = await runAnalysis({
        files,
        site,
        columnMappings: columnMappings as Record<string, unknown>,
        siteConfigOverrides: siteConfigOverrides as Record<string, unknown>,
        lang,
      });
      setAnalysisResult(result);
      if (assumptionsConfirmed) {
        savePerformancePreviewSnapshot(params.siteId, result);
      }
      setAnalysisSignature(previewSignature);
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : "REVEAL could not analyse the uploaded dataset.");
    }
  }, [site, filesReadyForReview, isRunningAnalysis, params.siteId, columnMappings, files, runAnalysis, previewSignature, assumptionsConfirmed, siteConfigOverrides]);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setJobId(null);
      setDetectionProgress(8);
      setDetectionProgressLabel(
        accepted.length === 1 ? `Analysing ${accepted[0]?.name ?? "uploaded file"}` : `Analysing ${accepted.length} uploaded files`
      );
      setFiles((prev) => {
        const nextFiles = [...prev, ...accepted];
        void autoDetectColumns(nextFiles);
        return nextFiles;
      });
    },
    [site]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.ms-excel": [".xls", ".xlsx"] },
    multiple: true,
  });

  async function handleGenerate() {
    if (files.length === 0 || !assumptionsConfirmed) return;
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("siteId", params.siteId);
      form.append("reportType", reportType);
      form.append("lang", lang);
      if (reportDate) form.append("reportDate", reportDate);
      form.append("columnMappings", JSON.stringify(columnMappings));
      form.append("siteConfigOverrides", JSON.stringify(siteConfigOverrides));
      files.forEach((f) => form.append("files", f));

      const { jobId: id } = await api.reports.createJob(form);
      setJobId(id);
      setCollapsedSteps((prev) => ({ ...prev, 4: false }));
    } finally {
      setSubmitting(false);
    }
  }

  async function detectFileColumns(file: File, worksheet?: string) {
    if (!site) {
      throw new Error("Site configuration is not available yet.");
    }
    return detectColumns({ file, siteType: site.site_type, worksheet });
  }

  async function autoDetectColumns(nextFiles: File[]) {
    setDetectionError(null);
    if (!site || nextFiles.length === 0) {
      setDetectedMappings({});
      setColumnMappings({});
      return;
    }

    try {
      const detections = await Promise.all(
        nextFiles.map(async (file) => [file.name, await detectFileColumns(file)] as const)
      );

      const detectionMap = Object.fromEntries(detections);
      setDetectedMappings(detectionMap);
      setColumnMappings(
        Object.fromEntries(
          detections.map(([filename, detection]) => [
            filename,
            {
              ...detection.mapping,
              worksheet: detection.selected_worksheet ?? undefined,
            },
          ])
        )
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Column detection failed.";
      setDetectionError(`Column detection error: ${msg}`);
    }
  }

  async function handleWorksheetChange(filename: string, worksheet: string) {
    const file = files.find((candidate) => candidate.name === filename);
    if (!file) return;

    setWorksheetLoadingFile(filename);
    try {
      const detection = await detectFileColumns(file, worksheet);
      setDetectedMappings((previous) => ({
        ...previous,
        [filename]: detection,
      }));
      setColumnMappings((previous) => ({
        ...previous,
        [filename]: {
          ...detection.mapping,
          worksheet: detection.selected_worksheet ?? worksheet,
        },
      }));
    } finally {
      setWorksheetLoadingFile((current) => (current === filename ? null : current));
    }
  }

  function updateReportType(nextType: ReportType) {
    setAnalysisChosen(true);
    const paramsObject = new URLSearchParams(searchParams.toString());
    paramsObject.set("type", nextType);
    router.replace(`?${paramsObject.toString()}`, { scroll: false });
  }

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/report-generate-hero.jpg" alt="Performance generation hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.9),rgba(5,30,45,0.76),rgba(5,30,45,0.64))]" />
      </div>

      <div className="relative px-8 py-8">
        <div className="space-y-6">
          <BackLink href={`/dashboard/site/${params.siteId}`} label="Back to site page" />

          <section className="rounded-[30px] border border-white/10 bg-[rgba(3,16,26,0.76)] p-6 backdrop-blur-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
                <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">
                  {t("reports.title")} {site ? `· ${site.display_name}` : ""}
                </h1>
                <p className="max-w-4xl text-sm leading-7 text-slate-200/82">
                  Move from uploaded operating data to a client-ready performance diagnosis through a clear step flow: choose the
                  analysis depth, upload and map the measured data, confirm the site context and data availability, then generate the
                  final technical summary and PDF.
                </p>
              </div>
            </div>
          </section>

          <div className="space-y-4">
            <WorkflowPanel
              step="Step 1"
              title="Choose analysis depth"
              description="Pick the performance workflow that best matches the dataset and the level of diagnosis the client needs."
              accent={currentAnalysis.accent}
              active={activeStep === 1}
              completed={step1Configured}
              collapsed={collapsedSteps[1]}
              onToggle={() => setCollapsedSteps((prev) => ({ ...prev, 1: !prev[1] }))}
              summary={
                step1Configured
                  ? `${currentAnalysis.stepLabel} selected in ${lang === "en" ? "English" : lang === "fr" ? "French" : "German"}. ${currentAnalysis.description}`
                  : "Choose the analysis depth and summary language to unlock Step 2."
              }
            >
              <div className="grid gap-4 xl:grid-cols-3">
                {ANALYSIS_OPTIONS.map((option) => {
                  const selected = option.type === reportType;
                  return (
                    <button
                      key={option.type}
                      type="button"
                      onClick={() => updateReportType(option.type)}
                      className={`rounded-[24px] border p-5 text-left transition ${
                        selected
                          ? "border-white/35 bg-[rgba(255,255,255,0.08)] shadow-[0_18px_38px_rgba(0,0,0,0.22)]"
                          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/7"
                      }`}
                    >
                      <div className={`h-1.5 w-24 rounded-full bg-gradient-to-r ${option.accent}`} />
                      <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-white/52">{option.stepLabel}</p>
                      <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">{option.title}</p>
                      <p className="mt-3 text-sm leading-7 text-slate-200/84">{option.description}</p>
                    </button>
                  );
                })}
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto]">
                {(reportType === "daily" || reportType === "monthly") && (
                  <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                    <label className="mb-1 block text-xs text-slate-400">{t("common.reportDate")}</label>
                    <input
                      type="date"
                      value={reportDate}
                      onChange={(e) => setReportDate(e.target.value)}
                      onFocus={selectAllOnFocus}
                      className="rounded-xl border border-white/15 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                    />
                    <p className="mt-2 text-xs leading-6 text-white/55">
                      Use this to anchor a daily or monthly summary PDF to the client reporting period.
                    </p>
                  </div>
                )}

                <div className="rounded-[22px] border border-white/10 bg-white/5 p-4">
                  <label className="mb-3 block text-xs text-slate-400">{t("reports.lang")}</label>
                  <div className="flex flex-wrap gap-2">
                    {(["en", "fr", "de"] as const).map((l) => (
                      <button
                        key={l}
                        type="button"
                        onClick={() => {
                          setLang(l);
                          setLanguageChosen(true);
                        }}
                        className={`rounded-xl border px-4 py-2 text-sm font-semibold transition-colors ${
                          lang === l
                            ? "border-orange-DEFAULT bg-orange-DEFAULT text-white shadow-[0_8px_24px_rgba(234,120,36,0.35)]"
                            : "border-white/12 bg-navy-light/80 text-slate-300 hover:border-orange-DEFAULT/40 hover:text-white"
                        }`}
                      >
                        {l === "en" ? "English" : l === "fr" ? "Français" : "Deutsch"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </WorkflowPanel>

            <WorkflowPanel
              step="Step 2"
              title="Upload actual data"
              description="Drop the measured SCADA workbook here, let REVEAL analyse the structure, and confirm the detected columns before the performance diagnosis begins."
              accent="from-sky-400/95 to-sky-600/70"
              active={activeStep === 2}
              completed={filesReadyForReview}
              collapsed={collapsedSteps[2]}
              onToggle={() => setCollapsedSteps((prev) => ({ ...prev, 2: !prev[2] }))}
              summary={
                previewReady
                  ? `${files.length} file(s) analysed. ${totalRows.toLocaleString()} rows detected across ${formatDateRange(firstRange)} and the availability heat map is ready.`
                  : analysisError
                    ? `${files.length} file(s) analysed. ${totalRows.toLocaleString()} rows detected across ${formatDateRange(firstRange)}. The optional heat-map preview failed, but you can continue to Step 3.`
                    : dataConfirmed
                      ? `${files.length} file(s) analysed. ${totalRows.toLocaleString()} rows detected across ${formatDateRange(firstRange)}. Uploaded data and mappings confirmed.`
                  : files.length > 0
                    ? "REVEAL is analysing the uploaded files and waiting for you to confirm the mapped data before Step 3."
                    : "No measured file uploaded yet."
              }
            >
              <div className="rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.82)] p-4 backdrop-blur-sm">
                <div
                  {...getRootProps()}
                  className={`rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${
                    isDragActive
                      ? "border-orange-DEFAULT bg-orange-DEFAULT/10"
                      : "cursor-pointer border-white/20 bg-[rgba(255,255,255,0.04)] hover:border-orange-DEFAULT/60"
                  }`}
                >
                  <input {...getInputProps()} />
                  <p className="text-sm font-medium text-slate-100">{isDragActive ? t("common.dropFiles") : t("common.dragDrop")}</p>
                  <p className="mt-2 text-xs leading-6 text-white/55">
                    Accepted formats: CSV, XLS, XLSX. REVEAL will detect timestamps, power, irradiance, ambient temperature, and module temperature automatically when available.
                  </p>
                </div>

                {files.length > 0 ? (
                  <ul className="mt-4 space-y-2">
                    {files.map((f, i) => (
                      <li
                        key={`${f.name}-${i}`}
                        className="flex items-center justify-between rounded-xl border border-white/8 bg-[rgba(255,255,255,0.05)] px-3 py-2 text-xs text-slate-100"
                      >
                        <span>{f.name}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const nextFiles = files.filter((_, j) => j !== i);
                            setFiles(nextFiles);
                            setJobId(null);
                            void autoDetectColumns(nextFiles);
                          }}
                          className="ml-2 text-slate-500 hover:text-danger"
                        >
                          ✕
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}

                {files.length > 0 ? (
                  <div className="mt-4 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Measured data analysis</p>
                        <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                          {isDetecting ? detectionProgressLabel || "Analysing uploaded file" : filesReadyForReview ? "Column analysis complete" : "Awaiting analysis"}
                        </p>
                      </div>
                      <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                        {isDetecting ? `${detectionProgress}%` : filesReadyForReview ? "100%" : "0%"}
                      </div>
                    </div>
                    <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                      <div
                        className="h-full rounded-full bg-[linear-gradient(90deg,rgba(88,176,255,0.96),rgba(125,211,252,0.96))] transition-all duration-500"
                        style={{ width: `${isDetecting ? detectionProgress : filesReadyForReview ? 100 : 0}%` }}
                      />
                    </div>
                    <p className="mt-3 text-sm text-slate-300/84">
                      {isDetecting
                        ? "REVEAL is scanning the CSV/XLSX structure, proposing column roles, and detecting the measured date range."
                        : "Columns detected. Please review and confirm the mappings below before moving to the site details step."}
                    </p>
                  </div>
                ) : null}
              </div>

              {detectionError ? (
                <div className="mt-5 rounded-[22px] border border-red-300/25 bg-red-500/10 px-5 py-4">
                  <p className="text-sm font-semibold text-red-100">Column detection failed</p>
                  <p className="mt-1 text-xs leading-6 text-red-100/80">{detectionError}</p>
                </div>
              ) : null}

              {files.length > 0 && site ? (
                <div className="mt-5">
                        <ColumnMapper
                          files={files}
                          siteType={site.site_type}
                          onMappingChange={setColumnMappings}
                          onWorksheetChange={handleWorksheetChange}
                          detectedMappings={detectedMappings}
                          worksheetLoadingFile={worksheetLoadingFile}
                        />
                </div>
              ) : null}

              {filesReadyForReview ? (
                <div className="mt-5 rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.84)] p-5 backdrop-blur-sm">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Data-availability heat map</p>
                      <p className="mt-2 text-sm leading-7 text-slate-200/82">
                        REVEAL previews monthly data quality across the inverter fleet here, separating missing data from frozen data. For solar, the preview is calculated over local daylight hours only, so overnight zeroes do not count against the coverage metrics.
                      </p>
                    </div>
                    {isRunningAnalysis ? (
                      <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-100">
                        Analysing…
                      </span>
                    ) : analysisResult ? (
                      <span className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-100">
                        Preview ready
                      </span>
                    ) : analysisError ? (
                      <span className="rounded-full border border-amber-300/25 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-amber-100">
                        Preview skipped
                      </span>
                    ) : null}
                  </div>

                  {analysisError ? (
                    <div className="mt-4 rounded-2xl border border-amber-300/25 bg-amber-400/10 px-4 py-4">
                      <p className="text-sm leading-7 text-amber-50">
                        REVEAL could not load the optional heat-map preview for this dataset. You can continue to Step 3, or retry the preview here.
                      </p>
                      <p className="mt-2 text-xs leading-6 text-amber-100/82">{analysisError}</p>
                      <div className="mt-4">
                        <Button variant="secondary" size="sm" onClick={requestPreview} disabled={isRunningAnalysis}>
                          Retry heat-map preview
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  {isRunningAnalysis ? (
                    <div className="mt-4 rounded-[22px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Heat-map preview</p>
                          <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                            {previewProgressLabel || "Building the data-quality preview"}
                          </p>
                        </div>
                        <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                          {previewProgress}%
                        </div>
                      </div>
                      <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                        <div
                          className="h-full rounded-full bg-[linear-gradient(90deg,rgba(88,176,255,0.96),rgba(125,211,252,0.96))] transition-all duration-500"
                          style={{ width: `${previewProgress}%` }}
                        />
                      </div>
                      <p className="mt-3 text-sm text-slate-300/84">
                        REVEAL is calculating monthly data quality, identifying missing versus frozen periods, and preparing the inverter heat map.
                      </p>
                    </div>
                  ) : null}

                  {analysisResult ? (
                    <>
                      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Power completeness</p>
                          <p className="mt-2 text-xl font-semibold text-white">{analysisResult.data_quality.overall_power_pct.toFixed(1)}%</p>
                        </div>
                        <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Irradiance completeness</p>
                          <p className="mt-2 text-xl font-semibold text-white">{analysisResult.data_quality.irradiance_pct.toFixed(1)}%</p>
                        </div>
                        <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Site mean availability</p>
                          <p className="mt-2 text-xl font-semibold text-white">{analysisResult.availability.mean_pct.toFixed(1)}%</p>
                        </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Whole-site outages</p>
                        <p className="mt-2 text-xl font-semibold text-white">{analysisResult.availability.whole_site_events}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 xl:grid-cols-2">
                      <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Availability assumptions</p>
                        <p className="mt-2 text-sm leading-7 text-slate-200/82">
                          For solar, REVEAL calculates preview completeness over the local daylight window only, using the same daytime screen as the long-term workflow. Overnight zeroes do not count as missing data.
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Whole-site outages definition</p>
                        <p className="mt-2 text-sm leading-7 text-slate-200/82">
                          This counts daytime periods where all mapped power channels are effectively offline at the same time, indicating a plant-wide outage rather than an isolated inverter event.
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 overflow-x-auto rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.03)]">
                        <div className="min-w-[760px]">
                          <div
                            className="grid gap-2 border-b border-white/10 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/50"
                            style={{ gridTemplateColumns: `120px repeat(${heatMapMonths.length}, minmax(72px, 1fr))` }}
                          >
                            <div>Inverter</div>
                            {heatMapMonths.map((month) => (
                              <div key={month} className="text-center">
                                {formatMonthLabel(month)}
                              </div>
                            ))}
                          </div>
                          <div className="space-y-2 px-4 py-4">
                            {heatMapInverters.map((inverter) => (
                              <div
                                key={inverter}
                                className="grid gap-2"
                                style={{ gridTemplateColumns: `120px repeat(${heatMapMonths.length}, minmax(72px, 1fr))` }}
                              >
                                <div className="flex items-center rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white">
                                  {inverter}
                                </div>
                                  {heatMapMonths.map((month) => {
                                    const quality = heatMapLookup.get(`${month}::${inverter}`) ?? {
                                      completenessPct: 0,
                                      missingPct: 0,
                                      frozenPct: 0,
                                    };
                                    return (
                                      <div
                                        key={`${inverter}-${month}`}
                                        className={`rounded-xl border px-2 py-2 text-center text-xs font-semibold ${getHeatTileClass(quality)}`}
                                        title={`${inverter} · ${formatMonthLabel(month)} · ${quality.completenessPct.toFixed(1)}% valid · ${quality.missingPct.toFixed(1)}% missing · ${quality.frozenPct.toFixed(1)}% frozen`}
                                      >
                                        {quality.frozenPct > 0
                                          ? `F ${quality.frozenPct.toFixed(0)}%`
                                          : quality.missingPct > 0
                                            ? `M ${quality.missingPct.toFixed(0)}%`
                                            : `${quality.completenessPct.toFixed(0)}%`}
                                      </div>
                                    );
                                  })}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.18em]">
                        <span className="rounded-full border border-emerald-300/25 bg-emerald-400/15 px-3 py-1 text-emerald-50">95%+ valid data</span>
                        <span className="rounded-full border border-sky-300/25 bg-sky-400/18 px-3 py-1 text-sky-50">Reduced but usable coverage</span>
                        <span className="rounded-full border border-rose-300/30 bg-rose-400/18 px-3 py-1 text-rose-50">Missing data</span>
                        <span className="rounded-full border border-red-300/30 bg-red-500/18 px-3 py-1 text-red-50">Frozen data</span>
                        <span className="rounded-full border border-rose-300/30 bg-[linear-gradient(135deg,rgba(239,68,68,0.28)_0%,rgba(239,68,68,0.28)_49%,rgba(251,113,133,0.22)_51%,rgba(251,113,133,0.22)_100%)] px-3 py-1 text-white">Frozen + missing</span>
                      </div>
                    </>
                  ) : !analysisError ? (
                    <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200/82">
                      Click “Load heat-map preview” if you want REVEAL to render the monthly completeness view before moving on.
                    </div>
                  ) : null}

                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-4">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-white">Confirm the uploaded data and mapped columns</p>
                      <p className="text-xs leading-6 text-white/60">
                        Step 3 should only open after you confirm that the measured files, mapped power channels, irradiance signal, and optional temperatures look correct.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" onClick={requestPreview} disabled={!filesReadyForReview || isRunningAnalysis}>
                        {analysisResult ? "Refresh heat-map preview" : "Load heat-map preview"}
                      </Button>
                      <Button
                        variant={dataConfirmed ? "secondary" : "primary"}
                        onClick={() => setDataConfirmed(true)}
                        disabled={!filesReadyForReview}
                      >
                        {dataConfirmed ? "Data confirmed" : "Confirm uploaded data"}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : null}
            </WorkflowPanel>

            <WorkflowPanel
              step="Step 3"
              title="Confirm site details and data availability"
              description="Review the site context, detected time range, and mapped performance signals before you launch the performance analysis."
              accent="from-amber-300/95 to-amber-500/70"
              active={activeStep === 3}
              completed={assumptionsConfirmed}
              collapsed={collapsedSteps[3]}
              onToggle={() => setCollapsedSteps((prev) => ({ ...prev, 3: !prev[3] }))}
              summary={
                assumptionsConfirmed
                  ? "Site context and data-availability checks confirmed for this run."
                  : "Confirm the plant assumptions, equipment details, site tariff, module tilt, and irradiance basis before REVEAL generates the performance diagnosis."
              }
            >
              <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-[24px] border border-white/10 bg-[rgba(4,18,30,0.88)] p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Site context</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Site</p>
                      <p className="mt-2 text-sm font-semibold text-white">{site?.display_name ?? "Loading site..."}</p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Technology</p>
                      <p className="mt-2 text-sm font-semibold text-white">{site?.technology ?? "—"}</p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">DC capacity</p>
                      <p className="mt-2 text-sm font-semibold text-white">
                        {site ? `${site.cap_dc_kwp.toLocaleString()} kWp` : "—"}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">AC capacity</p>
                      <p className="mt-2 text-sm font-semibold text-white">
                        {inferredAcCapacityKw > 0 ? `${inferredAcCapacityKw.toLocaleString(undefined, { maximumFractionDigits: 1 })} kW` : "—"}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Inverter type</p>
                      <input
                        type="text"
                        value={inverterType}
                        onChange={(event) => setInverterType(event.target.value)}
                        onFocus={selectAllOnFocus}
                        className="mt-2 w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                        placeholder="Confirm inverter model"
                      />
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Inverter quantity</p>
                      <input
                        type="number"
                        min="0"
                        value={inverterQuantity}
                        onChange={(event) => setInverterQuantity(event.target.value)}
                        onFocus={selectAllOnFocus}
                        className="mt-2 w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                        placeholder="e.g. 31"
                      />
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Module quantity</p>
                      <input
                        type="number"
                        min="0"
                        value={moduleQuantity}
                        onChange={(event) => setModuleQuantity(event.target.value)}
                        onFocus={selectAllOnFocus}
                        className="mt-2 w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                        placeholder="e.g. 16800"
                      />
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Module capacity</p>
                      <div className="mt-2 flex items-center gap-2">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={moduleCapacityWp}
                          onChange={(event) => setModuleCapacityWp(normalizeDecimalInput(event.target.value))}
                          onFocus={selectAllOnFocus}
                          className="w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                          placeholder="e.g. 660"
                        />
                        <span className="text-sm font-semibold text-white/70">Wp</span>
                      </div>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Site tariff</p>
                      <div className="mt-2 flex items-center gap-2">
                        <input
                          type="text"
                          inputMode="decimal"
                          value={siteTariffEurMwh}
                          onChange={(event) => setSiteTariffEurMwh(normalizeDecimalInput(event.target.value))}
                          onFocus={selectAllOnFocus}
                          className="w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                          placeholder="e.g. 85"
                        />
                        <span className="text-sm font-semibold text-white/70">EUR/MWh</span>
                      </div>
                      <p className="mt-2 text-xs leading-6 text-white/55">Required so REVEAL can later translate recoverable losses into owner value.</p>
                    </div>
                    {site?.site_type === "solar" ? (
                      <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Module tilt</p>
                        <div className="mt-2 flex items-center gap-2">
                          <input
                            type="text"
                            inputMode="decimal"
                            value={moduleTiltDeg}
                            onChange={(event) => setModuleTiltDeg(normalizeDecimalInput(event.target.value))}
                            onFocus={selectAllOnFocus}
                            className="w-full rounded-xl border border-white/12 bg-white px-3 py-2 text-sm font-medium text-slate-900 focus:border-orange-DEFAULT focus:outline-none"
                            placeholder="e.g. 20"
                          />
                          <span className="text-sm font-semibold text-white/70">deg</span>
                        </div>
                      </div>
                    ) : null}
                    {site?.site_type === "solar" ? (
                      <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Irradiance basis</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {[
                            { value: "poa", label: "POA" },
                            { value: "ghi", label: "GHI" },
                          ].map((option) => (
                            <button
                              key={option.value}
                              type="button"
                              onClick={() => setIrradianceBasis(option.value as "poa" | "ghi")}
                              className={`rounded-xl border px-3 py-2 text-sm font-semibold transition-colors ${
                                irradianceBasis === option.value
                                  ? "border-orange-DEFAULT bg-orange-DEFAULT text-white shadow-[0_8px_24px_rgba(234,120,36,0.35)]"
                                  : "border-white/12 bg-navy-light/80 text-slate-300 hover:border-orange-DEFAULT/40 hover:text-white"
                              }`}
                            >
                              {option.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-[24px] border border-white/10 bg-[rgba(4,18,30,0.88)] p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Data availability</p>
                  <div className="mt-4 space-y-3 text-sm text-slate-100">
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Files analysed</p>
                      <p className="mt-2 font-semibold text-white">{files.length}</p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Detected rows</p>
                      <p className="mt-2 font-semibold text-white">{totalRows.toLocaleString()}</p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Date range</p>
                      <p className="mt-2 font-semibold text-white">{formatDateRange(firstRange)}</p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Mapped power signals</p>
                      <p className="mt-2 font-semibold text-white">{powerColumnsSelected.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.04)] px-5 py-4">
                <div className="space-y-2">
                  <p className="text-sm leading-7 text-slate-200/84">
                    Confirm that the uploaded period, plant context, equipment details, site tariff, module tilt, and irradiance basis are correct before REVEAL generates the performance diagnosis and PDF summary.
                  </p>
                  <p className="text-xs leading-6 text-white/55">
                    If this is a brand-new asset, create the site in REVEAL first so Step 3 can pull the correct plant details, capacities, and technology.
                  </p>
                </div>
                <Button
                  variant="primary"
                  className={`font-semibold text-white shadow-[0_14px_36px_rgba(240,120,32,0.42)] ${assumptionsConfirmed ? "opacity-100" : "bg-orange-DEFAULT text-white hover:bg-orange-DEFAULT/90"}`}
                  onClick={() => {
                    setAssumptionsConfirmed(true);
                    setAnalysisLaunched(false);
                    setAnalysisResult(null);
                    setAnalysisError(null);
                    setAnalysisRequested(false);
                  }}
                  disabled={!filesReadyForReview || !dataConfirmed || !siteDetailsReady}
                >
                  {assumptionsConfirmed ? "Confirmed" : "Confirm assumptions"}
                </Button>
              </div>
              {assumptionsConfirmed ? (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-4 rounded-[22px] border border-violet-300/18 bg-[linear-gradient(135deg,rgba(124,58,237,0.18),rgba(59,130,246,0.08))] px-5 py-4">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-white">Launch the live analysis</p>
                    <p className="text-xs leading-6 text-white/65">
                      Trigger the full Step 4 diagnosis now to build the charts, commentary, waterfall, and punchlist in the app.
                    </p>
                    {dcAcRatio !== null && (dcAcRatio < 0.9 || dcAcRatio > 1.5) ? (
                      <p className="rounded-xl border border-amber-300/30 bg-amber-400/12 px-3 py-2 text-xs leading-6 text-amber-50">
                        Warning: the current DC/AC ratio is <span className="font-semibold text-white">{dcAcRatio.toFixed(2)}</span>. REVEAL expects most solar sites to sit roughly between <span className="font-semibold text-white">0.9</span> and <span className="font-semibold text-white">1.5</span>, so please double-check the inverter quantity or plant capacities before launching the analysis.
                      </p>
                    ) : null}
                  </div>
                  <Button
                    variant="primary"
                    className="font-semibold text-white shadow-[0_14px_34px_rgba(139,92,246,0.36)]"
                    onClick={async () => {
                      setAnalysisLaunched(true);
                      setCollapsedSteps((prev) => ({ ...prev, 4: false }));
                      await requestPreview();
                    }}
                    disabled={isRunningAnalysis}
                  >
                    {analysisResult && analysisSignature === previewSignature ? "Refresh analysis" : "Launch analysis"}
                  </Button>
                </div>
              ) : null}
            </WorkflowPanel>

            <WorkflowPanel
              step="Step 4"
              title="Review the analysis and export"
              description="Review the charts, commentary, KPIs, and punchlist directly in REVEAL first. Then generate the client-ready export as an extra deliverable."
              accent="from-violet-300/95 to-violet-500/70"
              active={activeStep === 4}
              completed={Boolean(jobId)}
              collapsed={collapsedSteps[4]}
              activeTone="dark"
              onToggle={() => setCollapsedSteps((prev) => ({ ...prev, 4: !prev[4] }))}
                summary={
                  jobId
                    ? "The performance analysis job is running or complete. Use the progress panel below to monitor the PDF generation."
                    : analysisResult
                      ? "The live diagnosis is ready in-app. Review the KPIs and punchlist, then generate the client-ready summary export if you need it."
                      : analysisLaunched
                        ? "REVEAL is preparing the in-app diagnosis now. The legacy summary export stays optional and secondary."
                        : assumptionsConfirmed
                          ? "Assumptions are confirmed. Launch the analysis when you are ready to open the full Step 4 diagnosis."
                        : "Once the assumptions are confirmed, REVEAL will run the live diagnosis in-app and keep the legacy summary export as an optional extra."
                }
              >
              {analysisLaunched && isRunningAnalysis ? (
                <div className="mb-5 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Analysis generation</p>
                      <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                        {analysisProgressLabel || "Generating the in-app performance analysis"}
                      </p>
                    </div>
                    <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                      {analysisProgress}%
                    </div>
                  </div>
                  <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                    <div
                      className="h-full rounded-full bg-[linear-gradient(90deg,rgba(168,85,247,0.96),rgba(125,211,252,0.96))] transition-all duration-500"
                      style={{ width: `${analysisProgress}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm text-slate-300/84">
                    REVEAL is building the loss breakdown, the performance commentary, and the chart set that drives the comprehensive in-app diagnosis.
                  </p>
                </div>
              ) : null}
              <div className="space-y-4">
                <div className="rounded-[24px] border border-white/10 bg-white/5 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Executive summary</p>
                  {analysisResult ? (
                    <>
                      <div className="mt-4 rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.035)] p-4">
                        <div className="space-y-3 text-sm leading-7 text-slate-200/84">
                          {executiveSummary.map((line, index) => (
                            <p key={index}>{line}</p>
                          ))}
                        </div>
                      </div>

                        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                          <div className="h-full rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                            <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Total measured energy</p>
                            <p className="mt-2 text-2xl font-semibold text-white">{totalEnergyMwh.toFixed(1)} MWh</p>
                          </div>
                          <div className="h-full rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                            <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Mean availability</p>
                            <p className="mt-2 text-2xl font-semibold text-white">{analysisResult.availability.mean_pct.toFixed(1)}%</p>
                          </div>
                          <div className="h-full rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                            <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Latest annual PR</p>
                            <p className="mt-2 text-2xl font-semibold text-white">
                              {latestAnnualPr.toFixed(1)}%
                            </p>
                          </div>
                          <div className="h-full rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                            <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Annualised site specific yield</p>
                            <p className="mt-2 text-2xl font-semibold text-white">
                            {annualisedSiteSpecificYield.toFixed(1)} kWh/kWp/yr
                          </p>
                        </div>
                        <div className="h-full rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                          <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Whole-site outages</p>
                          <p className="mt-2 text-2xl font-semibold text-white">{analysisResult.availability.whole_site_events}</p>
                        </div>
                      </div>

                      <div className="mt-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Main improvement points</p>
                        <div className="mt-3 space-y-3">
                          {topPunchlist.length > 0 ? (
                            topPunchlist.map((item, index) => (
                              <div key={`${item.category}-${index}`} className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.03)] p-4">
                                <div className="flex flex-wrap items-center gap-3">
                                  <span
                                    className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                                      item.priority === "HIGH"
                                        ? "border border-rose-300/25 bg-rose-400/12 text-rose-50"
                                        : item.priority === "MEDIUM"
                                          ? "border border-amber-300/25 bg-amber-400/12 text-amber-50"
                                          : "border border-sky-300/25 bg-sky-400/12 text-sky-50"
                                    }`}
                                  >
                                    {item.priority}
                                  </span>
                                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/45">{item.category}</span>
                                </div>
                                <p className="mt-3 text-sm font-semibold text-white">{item.finding}</p>
                                <p className="mt-2 text-sm leading-7 text-slate-200/82">{item.recommendation}</p>
                              </div>
                            ))
                          ) : (
                            <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.03)] p-4 text-sm text-slate-200/82">
                              REVEAL has not identified any punchlist items in the current preview.
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-5">
                        <AnalysisSection
                          id="Lead section"
                          title="Yield waterfall and core bridge"
                          description="This is the lead view of the performance diagnosis. It bridges design expectation to actual yield, separates baseline non-recoverable effects from recoverable losses, and keeps any unexplained remainder in an explicit over / under-performance bucket."
                          collapsed={collapsedAnalysisSections.overview}
                          onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, overview: !prev.overview }))}
                        >
                          <div className="mb-4 rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.035)] p-5">
                            <div className="flex flex-wrap items-end gap-4">
                              <MonthFieldPicker
                                label="Waterfall start"
                                value={waterfallStartMonthDraft}
                                min={analysisMonths[0]}
                                max={waterfallEndMonthDraft || analysisMonths[analysisMonths.length - 1]}
                                onChange={setWaterfallStartMonthDraft}
                              />
                              <MonthFieldPicker
                                label="Waterfall end"
                                value={waterfallEndMonthDraft}
                                min={waterfallStartMonthDraft || analysisMonths[0]}
                                max={analysisMonths[analysisMonths.length - 1]}
                                onChange={setWaterfallEndMonthDraft}
                              />
                              <div className="min-w-[180px]">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/45">Apply period</p>
                                <Button
                                  variant="primary"
                                  className="mt-2 w-full font-semibold text-white"
                                  onClick={() => {
                                    setWaterfallStartMonth(waterfallStartMonthDraft);
                                    setWaterfallEndMonth(waterfallEndMonthDraft);
                                  }}
                                  disabled={
                                    !waterfallStartMonthDraft ||
                                    !waterfallEndMonthDraft ||
                                    waterfallStartMonthDraft > waterfallEndMonthDraft ||
                                    (waterfallStartMonthDraft === waterfallStartMonth && waterfallEndMonthDraft === waterfallEndMonth)
                                  }
                                >
                                  Update chart
                                </Button>
                              </div>
                              <div className="min-w-[240px] flex-1 rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.03)] px-4 py-3">
                                <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Selected period</p>
                                <p className="mt-2 text-sm font-semibold text-white">
                                  {effectiveWaterfallStartMonth && effectiveWaterfallEndMonth
                                    ? `${formatMonthLabel(effectiveWaterfallStartMonth)} to ${formatMonthLabel(effectiveWaterfallEndMonth)}`
                                    : "Full analysed period"}
                                </p>
                                <p className="mt-2 text-xs leading-6 text-white/55">
                                  This first version filters the waterfall to the selected months and prorates the bridge buckets to that period so you can compare summer, winter, or any custom slice.
                                </p>
                              </div>
                            </div>
                          </div>
                          <ChartShell
                            title="Yield waterfall"
                            description="Start here. This bridge shows how REVEAL moves from design yield through weather-corrected yield to actual yield, with the main loss buckets laid out in the order the owner should question them."
                            heightClass="h-[396px]"
                          >
                            <div className="h-full">
                              <WaterfallChart data={filteredWaterfallContext.chartData} />
                            </div>
                          </ChartShell>

                          <div className="mt-4 rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.035)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Waterfall commentary</p>
                            <div className="mt-4 space-y-3 text-sm leading-7 text-slate-200/84">
                              <p>
                                REVEAL starts from a measured-weather design expectation, then subtracts baseline non-recoverable effects such as design derate and temperature. That creates the weather-corrected yield.
                              </p>
                              <p>
                                From there, REVEAL isolates the recoverable losses that matter most for owners: downtime, curtailment / negative-hour behaviour, and site-side mismatch or soiling effects.
                              </p>
                              <p>
                                Any remaining unexplained difference is kept in the <span className="font-semibold text-white">over / under performance</span> bucket so it can be tested later in the digital twin rather than hidden inside other assumptions.
                              </p>
                              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                                <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Design yield</p>
                                  <p className="mt-2 text-xl font-semibold text-white">{filteredWaterfallContext.designYieldMwh.toFixed(1)} MWh</p>
                                </div>
                                <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Weather-corrected yield</p>
                                  <p className="mt-2 text-xl font-semibold text-white">{filteredWaterfallContext.weatherCorrectedYieldMwh.toFixed(1)} MWh</p>
                                </div>
                                <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Recoverable losses</p>
                                  <p className="mt-2 text-xl font-semibold text-white">{filteredWaterfallContext.recoverableMwh.toFixed(1)} MWh</p>
                                </div>
                                <div className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.035)] px-4 py-3">
                                  <p className="text-[11px] uppercase tracking-[0.22em] text-white/40">Over / under performance</p>
                                  <p className="mt-2 text-xl font-semibold text-white">{filteredWaterfallContext.overUnderPerformanceMwh.toFixed(1)} MWh</p>
                                </div>
                              </div>
                            </div>
                          </div>
                        </AnalysisSection>
                      </div>

                      <AnalysisSection
                        id="Section A"
                        title="Weather context and rainfall heat map"
                        description="ERA rainfall is shown here to support later excess-soiling interpretation. REVEAL highlights heavy and very heavy rainfall months and the strongest cleaning-event candidates."
                        collapsed={collapsedAnalysisSections.weather}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, weather: !prev.weather }))}
                      >
                        {weatherMonthlyRows.length > 0 ? (
                          <>
                            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                              <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Weather source</p>
                                <p className="mt-3 text-lg font-semibold text-white">{analysisResult?.weather.source ?? "ERA rainfall"}</p>
                              </div>
                              <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Total rain</p>
                                <p className="mt-3 text-lg font-semibold text-white">{weatherSummary?.total_rain_mm.toFixed(1) ?? "0.0"} mm</p>
                              </div>
                              <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Heavy rain days</p>
                                <p className="mt-3 text-lg font-semibold text-white">{weatherSummary?.heavy_rain_days ?? 0}</p>
                              </div>
                              <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Very heavy rain days</p>
                                <p className="mt-3 text-lg font-semibold text-white">{weatherSummary?.very_heavy_rain_days ?? 0}</p>
                              </div>
                            </div>

                            <div className="mt-4 rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Rainfall heat map</p>
                              <p className="mt-2 text-sm leading-7 text-slate-200/82">
                                Higher monthly rainfall is shown in stronger red tones, and very extreme wet months turn pale toward white. This is the weather context REVEAL will use when checking whether heavy rainfall coincides with a PR reset that could confirm excess soiling.
                              </p>
                              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                                {weatherMonthlyRows.map((item) => {
                                  const style = getRainHeatTileStyle(item.total_rain_mm);
                                  return (
                                    <div
                                      key={item.month}
                                      className="rounded-2xl border px-4 py-4"
                                      style={style}
                                    >
                                      <div className="flex items-center justify-between gap-3">
                                        <p className="text-sm font-semibold">{formatMonthLabel(item.month)}</p>
                                        <span className="rounded-full border border-current/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]">
                                          {item.intensity.replace("_", " ")}
                                        </span>
                                      </div>
                                      <p className="mt-3 text-2xl font-semibold">{item.total_rain_mm.toFixed(1)} mm</p>
                                      <p className="mt-2 text-xs leading-6 opacity-80">
                                        Peak hourly rain {item.max_hourly_rain_mm.toFixed(2)} mm/h across {item.rainy_hours} rainy hour{item.rainy_hours === 1 ? "" : "s"}.
                                      </p>
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-white/72">
                                <span className="rounded-full border border-white/14 bg-white/6 px-3 py-1">Dry / negligible</span>
                                <span className="rounded-full border border-red-300/30 bg-red-400/10 px-3 py-1">Moderate rain</span>
                                <span className="rounded-full border border-red-300/45 bg-red-500/18 px-3 py-1">Heavy rain</span>
                                <span className="rounded-full border border-red-200/55 bg-red-200/20 px-3 py-1">Very heavy rain</span>
                                <span className="rounded-full border border-white/55 bg-white/75 px-3 py-1 text-slate-900">Extreme wet month</span>
                              </div>
                            </div>

                            <div className="mt-4 rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Heavy-rain event candidates</p>
                              <p className="mt-2 text-sm leading-7 text-slate-200/82">
                                These are the strongest heavy and very heavy rain days from ERA. They do not prove cleaning by themselves, but they give REVEAL the right event candidates to compare like-for-like PR before and after rain.
                              </p>
                              <div className="mt-4 overflow-x-auto">
                                <table className="min-w-full border-separate border-spacing-y-3 text-sm">
                                  <thead>
                                    <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-white/45">
                                      <th className="px-3 py-2">Date</th>
                                      <th className="px-3 py-2">Class</th>
                                      <th className="px-3 py-2">Daily rain</th>
                                      <th className="px-3 py-2">Peak hourly rain</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {weatherEvents.length > 0 ? (
                                      weatherEvents.map((item) => (
                                        <tr key={item.date} className="rounded-2xl border border-white/8 bg-white/5 text-slate-100">
                                          <td className="rounded-l-2xl px-3 py-3 font-semibold text-white">{item.date}</td>
                                          <td className="px-3 py-3">
                                            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                                              item.classification === "very heavy"
                                                ? "border border-red-200/50 bg-red-100/15 text-red-50"
                                                : "border border-red-300/30 bg-red-500/12 text-red-100"
                                            }`}>
                                              {item.classification}
                                            </span>
                                          </td>
                                          <td className="px-3 py-3 font-semibold">{item.total_rain_mm.toFixed(1)} mm</td>
                                          <td className="rounded-r-2xl px-3 py-3 text-slate-200/84">{item.peak_hourly_rain_mm.toFixed(2)} mm/h</td>
                                        </tr>
                                      ))
                                    ) : (
                                      <tr>
                                        <td colSpan={4} className="rounded-2xl border border-white/8 bg-white/5 px-3 py-4 text-slate-200/82">
                                          REVEAL did not find any heavy-rain candidates in the ERA record for this analysed period.
                                        </td>
                                      </tr>
                                    )}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm leading-7 text-slate-200/84">
                            {analysisResult?.weather.error
                              ? `REVEAL could not load ERA rainfall for this run: ${analysisResult.weather.error}`
                              : "REVEAL did not receive any rainfall context for this analysed period."}
                          </div>
                        )}
                      </AnalysisSection>

                      <AnalysisSection
                        id="Section B"
                        title="Monthly performance story and inverter spread"
                        description="This section keeps the main month-by-month comparison, the first-pass loss framing, and the best-versus-worst inverter spread together so it can be opened or collapsed as one block."
                        collapsed={collapsedAnalysisSections.site}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, site: !prev.site }))}
                      >
                      <div className="grid gap-4 xl:grid-cols-2">
                        <ChartShell
                          title="Monthly energy versus reference"
                          description="Actual site energy is compared against the weather-implied reference each month. This is the first view to check whether the underperformance is concentrated in specific periods or structural across the year."
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={latestMonths} margin={{ top: 20, right: 10, left: 10, bottom: 16 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                              <XAxis
                                dataKey="month"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                tickFormatter={formatMonthLabel}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Month", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <YAxis
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Energy (MWh)", angle: -90, position: "insideLeft", dy: 60, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <Tooltip content={<RevealTooltip labelFormatter={formatMonthLabel} valueSuffix=" MWh" />} cursor={false} />
                              <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
                              <Bar dataKey="E_act_mwh" name="Measured energy" fill="rgba(88,176,255,0.88)" radius={[5, 5, 0, 0]} />
                              <Line type="monotone" dataKey="E_ref_mwh" name="Reference energy" stroke="#f59e0b" strokeWidth={2.4} dot={false} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </ChartShell>

                        <ChartShell
                          title="Monthly PR and irradiation"
                          description="This chart helps separate weather from performance. Strong irradiation paired with weak PR points to recoverable operational issues rather than a poor solar resource month."
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={latestMonths} margin={{ top: 20, right: 12, left: 8, bottom: 16 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                              <XAxis
                                dataKey="month"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                tickFormatter={formatMonthLabel}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Month", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <YAxis
                                yAxisId="left"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "PR (%)", angle: -90, position: "insideLeft", dy: 56, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Irradiation (kWh/m²)", angle: 90, position: "insideRight", dy: 56, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <Tooltip content={<RevealTooltip labelFormatter={formatMonthLabel} />} cursor={false} />
                              <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
                              <Line yAxisId="left" type="monotone" dataKey="PR_pct" name="PR" stroke="#60a5fa" strokeWidth={2.4} dot={false} />
                              <Bar yAxisId="right" dataKey="irrad_kwh_m2" name="Irradiation" fill="rgba(245,158,11,0.75)" radius={[5, 5, 0, 0]} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </ChartShell>
                      </div>

                      <div className="mt-5 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                        <ChartShell
                          title="Recoverable versus non-recoverable losses"
                          description="REVEAL converts the production gap into first-pass loss buckets. The recoverable side is where corrective actions and the future digital twin should focus first."
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={lossBreakdown} layout="vertical" margin={{ top: 10, right: 10, left: 54, bottom: 10 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" horizontal={false} />
                              <XAxis
                                type="number"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Loss estimate (MWh)", position: "insideBottom", offset: -4, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <YAxis
                                type="category"
                                dataKey="label"
                                width={170}
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip content={<RevealTooltip valueSuffix=" MWh" />} cursor={false} />
                              <Bar dataKey="value_mwh" radius={[0, 6, 6, 0]}>
                                {lossBreakdown.map((item, index) => (
                                  <Cell
                                    key={`${item.label}-${index}`}
                                    fill={
                                      item.classification === "recoverable"
                                        ? "rgba(88,176,255,0.88)"
                                        : item.classification === "screened"
                                          ? "rgba(239,68,68,0.85)"
                                          : "rgba(148,163,184,0.7)"
                                    }
                                  />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </ChartShell>

                        <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Diagnosis commentary</p>
                          <div className="mt-4 space-y-3 text-sm leading-7 text-slate-200/84">
                            <p>
                              REVEAL now treats the performance section as an analytical layer rather than a report launcher. The focus is on isolating the likely causes of underperformance and separating recoverable losses from the residual non-recoverable gap.
                            </p>
                            {diagnosisCommentary.map((line, index) => (
                              <p key={`diagnosis-line-${index}`}>{line}</p>
                            ))}
                            <p>
                              These conclusions are heuristic at this stage. The next digital-twin layer should be used to confirm the curtailment and negative-hour assumptions before those losses are converted into a battery-retrofit case.
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
                        <ChartShell
                          title="Site availability trend"
                          description="Availability is shown alongside the monthly production story so equipment downtime can be separated from pure resource-driven variation."
                        >
                          <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={latestAvailabilityMonths} margin={{ top: 20, right: 10, left: 8, bottom: 16 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                              <XAxis
                                dataKey="month"
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                tickFormatter={formatMonthLabel}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Month", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <YAxis
                                domain={[0, 100]}
                                tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                tickLine={false}
                                label={{ value: "Availability (%)", angle: -90, position: "insideLeft", dy: 60, fill: "#cbd5e1", fontSize: 11 }}
                              />
                              <Tooltip content={<RevealTooltip labelFormatter={formatMonthLabel} valueSuffix="%" />} cursor={false} />
                              <Line type="monotone" dataKey="avail_pct" name="Availability" stroke="#34d399" strokeWidth={2.6} dot={false} />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </ChartShell>

                        <MetricBars
                          title="Inverter specific yield ranking"
                          description="REVEAL now shows only the top 2 and worst 2 inverters so the spread is easier to read without stretching the section."
                          rows={yieldRanking.map((item) => ({
                            label: item.inv_id,
                            value: item.yield_kwh_kwp,
                            secondary: `${item.rank <= 2 ? "Top performer" : "Lowest performer"} · PR ${item.pr_pct.toFixed(1)}% · Rank ${item.rank}`,
                          }))}
                          colorClass="bg-[linear-gradient(90deg,rgba(168,85,247,0.96),rgba(139,92,246,0.96))]"
                          valueSuffix=" kWh/kWp"
                        />
                      </div>

                      <div className="mt-5 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                        <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Root causes and actions</p>
                          <div className="mt-4 space-y-3">
                            {rootCauses.length > 0 ? (
                              rootCauses.map((item, index) => (
                                <div key={`${item.title}-${index}`} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                                  <div className="flex items-center gap-3">
                                    <span
                                      className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                                        item.recoverability === "recoverable"
                                          ? "border border-emerald-300/25 bg-emerald-400/12 text-emerald-50"
                                          : item.recoverability === "screened"
                                            ? "border border-red-300/25 bg-red-500/12 text-red-50"
                                            : "border border-slate-300/20 bg-slate-400/10 text-slate-100"
                                      }`}
                                    >
                                      {item.recoverability.replace("_", " ")}
                                    </span>
                                    <p className="font-semibold text-white">{item.title}</p>
                                  </div>
                                  <p className="mt-3 text-sm leading-7 text-slate-200/84">{item.cause}</p>
                                  <p className="mt-2 text-sm leading-7 text-white/68">{item.action}</p>
                                </div>
                              ))
                            ) : (
                              <div className="rounded-2xl border border-white/8 bg-white/5 p-4 text-sm text-slate-200/82">
                                REVEAL has not yet derived a clear root-cause chain from the current preview.
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Probable curtailment months</p>
                          <p className="mt-2 text-sm leading-7 text-slate-200/82">
                            These are months where irradiation stayed healthy and site availability remained high, but production still underperformed. They are the first candidates to carry into the digital-twin and BESS-retrofit logic.
                          </p>
                          <div className="mt-4 space-y-3">
                            {curtailmentCandidates.length > 0 ? (
                              curtailmentCandidates.map((item) => (
                                <div key={item.month} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                                  <div className="flex items-center justify-between gap-3">
                                    <p className="font-semibold text-white">{formatMonthLabel(item.month)}</p>
                                    <span className="rounded-full border border-amber-300/25 bg-amber-400/12 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-50">
                                      {item.confidence} confidence
                                    </span>
                                  </div>
                                  <p className="mt-3 text-sm leading-7 text-slate-200/84">
                                    {item.loss_mwh.toFixed(1)} MWh suppressed with PR at {item.pr_pct.toFixed(1)}%, availability at {item.availability_pct.toFixed(1)}%, and irradiation at {item.irradiation_kwh_m2.toFixed(1)} kWh/m².
                                  </p>
                                  <p className="mt-2 text-sm leading-7 text-white/68">{item.reason}</p>
                                </div>
                              ))
                            ) : (
                              <div className="rounded-2xl border border-white/8 bg-white/5 p-4 text-sm text-slate-200/82">
                                REVEAL did not isolate any strong curtailment months from the current preview. That may mean losses are being driven more by downtime or general underperformance than by export suppression.
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      </AnalysisSection>

                      <AnalysisSection
                        id="Section C"
                        title="Detailed inverter diagnostics annex"
                        description="These annex-style sections carry more of the analytical depth from the comprehensive PVPAT analysis into the app itself, with cleaner visuals for REVEAL."
                        collapsed={collapsedAnalysisSections.inverter}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, inverter: !prev.inverter }))}
                      >
                        <div className="grid gap-4 xl:grid-cols-2">
                          <MetricBars
                            title="Lowest MTTF units"
                            description="These are the least reliable inverters by mean time to failure. Frequent failure events point toward recoverable availability losses."
                            rows={mttfRanking.map((item) => ({
                              label: item.inv_id,
                              value: item.mttf_hours,
                              secondary: `${item.n_failures} failure events`,
                            }))}
                            colorClass="bg-[linear-gradient(90deg,rgba(251,146,60,0.96),rgba(239,68,68,0.96))]"
                            valueSuffix=" h"
                          />

                          <MetricBars
                            title="Start-delay outliers"
                            description="Late-start signatures often reveal threshold, wake-up, or control issues that would not be obvious from a simple monthly KPI view."
                            rows={startStopOutliers.map((item) => ({
                              label: item.inv_id,
                              value: Math.abs(item.start_dev),
                              secondary: `Average start ${item.start_label} · deviation ${item.start_dev.toFixed(1)} min`,
                            }))}
                            colorClass="bg-[linear-gradient(90deg,rgba(96,165,250,0.96),rgba(14,165,233,0.96))]"
                            valueSuffix=" min"
                          />
                        </div>

                        <div className="mt-4 grid gap-4 xl:grid-cols-2">
                          <ChartShell
                            title="Near-clipping frequency by irradiance"
                            description="This mirrors the clipping section from the comprehensive analysis. It shows whether the site is regularly operating close to the AC ceiling under strong irradiance."
                          >
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={clippingBins} margin={{ top: 20, right: 10, left: 8, bottom: 16 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                                <XAxis
                                  dataKey="label"
                                  tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                  axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                  tickLine={false}
                                  label={{ value: "Irradiance bin (W/m²)", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }}
                                />
                                <YAxis
                                  tick={{ fill: "#cbd5e1", fontSize: 11 }}
                                  axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
                                  tickLine={false}
                                  label={{ value: "Near-clipping frequency (%)", angle: -90, position: "insideLeft", dy: 60, fill: "#cbd5e1", fontSize: 11 }}
                                />
                                <Tooltip content={<RevealTooltip valueSuffix="%" />} cursor={false} />
                                <Bar dataKey="near_clip_pct" name="Near-clipping" fill="rgba(245,158,11,0.82)" radius={[5, 5, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </ChartShell>

                          <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Peer grouping and priority units</p>
                            <div className="mt-4 space-y-3">
                              {peerGroupRows.slice(0, 12).map((item) => (
                                <div key={item.inv_id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                    <p className="font-semibold text-white">{item.inv_id}</p>
                                    <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/82">
                                      {item.group}
                                    </span>
                                  </div>
                                  <p className="mt-3 text-sm leading-7 text-slate-200/84">
                                    PR {item.pr_pct.toFixed(1)}% · Availability {item.avail_pct.toFixed(1)}% · Start deviation {item.start_dev_min.toFixed(1)} min · Variability CV {item.variability_cv.toFixed(2)}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="mt-4">
                          <MetricBars
                            title="Top inverters by near-clipping occurrence"
                            description="These inverters spend the most time close to their AC ceiling and deserve follow-up where clipping, export limits, or design saturation are suspected."
                            rows={clippingInverters.map((item) => ({
                              label: item.inv_id,
                              value: item.near_clip_pct,
                              secondary: "Share of valid daytime intervals near the AC ceiling",
                            }))}
                            colorClass="bg-[linear-gradient(90deg,rgba(245,158,11,0.96),rgba(249,115,22,0.96))]"
                            valueSuffix="%"
                          />
                        </div>
                      </AnalysisSection>

                      <AnalysisSection
                        id="Section D"
                        title="Reliability benchmark and quantified loss punchlist"
                        description="These tables convert the technical diagnosis into owner-facing reliability and value language, using MTTF benchmarking and tariff-weighted loss impacts."
                        collapsed={collapsedAnalysisSections.actions}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, actions: !prev.actions }))}
                      >
                        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                          <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">MTTF versus benchmark</p>
                            <p className="mt-2 text-sm leading-7 text-slate-200/82">
                              REVEAL classifies inverter reliability against a simple industry-style operating benchmark:
                              below 750 h is weak, 750-1500 h is watch-list territory, and above 1500 h is comparatively resilient. We can tighten these thresholds later by OEM and climate.
                            </p>
                            <div className="mt-4 space-y-3">
                              {mttfBenchmarkedRows.slice(0, 10).map((item) => (
                                <div key={item.inv_id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                    <p className="font-semibold text-white">{item.inv_id}</p>
                                    <span
                                      className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                                        item.status === "Above industry benchmark"
                                          ? "border border-emerald-300/25 bg-emerald-400/12 text-emerald-50"
                                          : item.status === "Watch list"
                                            ? "border border-amber-300/25 bg-amber-400/12 text-amber-50"
                                            : "border border-red-300/25 bg-red-500/12 text-red-50"
                                      }`}
                                    >
                                      {item.status}
                                    </span>
                                  </div>
                                  <p className="mt-3 text-sm leading-7 text-slate-200/84">
                                    MTTF {item.mttf_hours.toFixed(0)} h across {item.n_failures} recorded failure event{item.n_failures === 1 ? "" : "s"}.
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Main loss sections and recommended actions</p>
                            <p className="mt-2 text-sm leading-7 text-slate-200/82">
                              This is the owner-facing punchlist. REVEAL expresses each loss section in energy, approximate value, and next action so recoverable losses can be prioritized properly.
                            </p>
                            <div className="mt-4 overflow-x-auto">
                              <table className="min-w-full border-separate border-spacing-y-3 text-sm">
                                <thead>
                                  <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-white/45">
                                    <th className="px-3 py-2">Loss section</th>
                                    <th className="px-3 py-2">Class</th>
                                    <th className="px-3 py-2">MWh</th>
                                    <th className="px-3 py-2">kEUR</th>
                                    <th className="px-3 py-2">Recommended action</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {lossActionRows.map((item) => (
                                    <tr key={item.label} className="rounded-2xl border border-white/8 bg-white/5 align-top text-slate-100">
                                      <td className="rounded-l-2xl px-3 py-3 font-semibold text-white">{item.label}</td>
                                      <td className="px-3 py-3">
                                        <span
                                          className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                                            item.classification === "recoverable"
                                              ? "border border-emerald-300/25 bg-emerald-400/12 text-emerald-50"
                                              : item.classification === "screened"
                                                ? "border border-red-300/25 bg-red-500/12 text-red-50"
                                                : "border border-slate-300/20 bg-slate-400/10 text-slate-100"
                                          }`}
                                        >
                                          {item.classification.replace("_", " ")}
                                        </span>
                                      </td>
                                      <td className="px-3 py-3 font-semibold">{item.value_mwh.toFixed(1)}</td>
                                      <td className="px-3 py-3 font-semibold">{item.value_keur.toFixed(1)}</td>
                                      <td className="rounded-r-2xl px-3 py-3 text-slate-200/84">{item.action}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            <p className="mt-3 text-xs leading-6 text-white/55">
                              Value conversion uses the confirmed site tariff of {tariffEurMwh.toFixed(1)} EUR/MWh. This is a first-order owner view, not yet a price-shape or market-dispatch valuation.
                            </p>
                          </div>
                        </div>
                      </AnalysisSection>

                      <AnalysisSection
                        id="Section E"
                        title="Performance trend and event overlay annex"
                        description="This annex carries the longer-form analytical views from the comprehensive report into REVEAL so you can inspect drift, instability, and event clustering directly in-app."
                        collapsed={collapsedAnalysisSections.losses}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, losses: !prev.losses }))}
                      >
                        <div className="grid gap-4 xl:grid-cols-2">
                          <ChartShell
                            title="Annual PR trend"
                            description="This is the in-app version of the degradation-style view. It tracks annual PR across the analysed period so drift can be spotted before it is treated as real degradation."
                          >
                            <ResponsiveContainer width="100%" height="100%">
                              <ComposedChart data={degradationTrendRows} margin={{ top: 20, right: 10, left: 8, bottom: 16 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                                <XAxis dataKey="year" tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "Year", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }} />
                                <YAxis yAxisId="left" tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "PR (%)", angle: -90, position: "insideLeft", dy: 60, fill: "#cbd5e1", fontSize: 11 }} />
                                <YAxis yAxisId="right" orientation="right" tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "Energy (MWh)", angle: 90, position: "insideRight", dy: 56, fill: "#cbd5e1", fontSize: 11 }} />
                                <Tooltip content={<RevealTooltip />} cursor={false} />
                                <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
                                <Line yAxisId="left" type="monotone" dataKey="pr_pct" name="Annual PR" stroke="#60a5fa" strokeWidth={2.6} dot />
                                <Bar yAxisId="right" dataKey="energy_mwh" name="Annual energy" fill="rgba(34,197,94,0.7)" radius={[5, 5, 0, 0]} />
                              </ComposedChart>
                            </ResponsiveContainer>
                          </ChartShell>

                          <ChartShell
                            title="Monthly event overlay"
                            description="This overlay combines PR, availability, missing data, frozen data, and probable curtailment. It is designed to show when multiple warning signals stack up in the same month."
                          >
                            <ResponsiveContainer width="100%" height="100%">
                              <ComposedChart data={monthlyTimelineRows} margin={{ top: 20, right: 10, left: 8, bottom: 16 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
                                <XAxis dataKey="month" tick={{ fill: "#cbd5e1", fontSize: 11 }} tickFormatter={formatMonthLabel} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "Month", position: "insideBottom", offset: -6, fill: "#cbd5e1", fontSize: 11 }} />
                                <YAxis yAxisId="left" domain={[0, 100]} tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "Percent (%)", angle: -90, position: "insideLeft", dy: 60, fill: "#cbd5e1", fontSize: 11 }} />
                                <YAxis yAxisId="right" orientation="right" tick={{ fill: "#cbd5e1", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.16)" }} tickLine={false} label={{ value: "Curtailment (MWh)", angle: 90, position: "insideRight", dy: 56, fill: "#cbd5e1", fontSize: 11 }} />
                                <Tooltip content={<RevealTooltip labelFormatter={formatMonthLabel} />} cursor={false} />
                                <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
                                <Line yAxisId="left" type="monotone" dataKey="pr_pct" name="PR" stroke="#60a5fa" strokeWidth={2.2} dot={false} />
                                <Line yAxisId="left" type="monotone" dataKey="availability_pct" name="Availability" stroke="#34d399" strokeWidth={2.2} dot={false} />
                                <Bar yAxisId="left" dataKey="missing_pct" name="Missing data" fill="rgba(244,114,182,0.58)" radius={[4, 4, 0, 0]} />
                                <Bar yAxisId="left" dataKey="frozen_pct" name="Frozen data" fill="rgba(220,38,38,0.72)" radius={[4, 4, 0, 0]} />
                                <Bar yAxisId="right" dataKey="curtailment_mwh" name="Curtailment candidate" fill="rgba(245,158,11,0.72)" radius={[4, 4, 0, 0]} />
                              </ComposedChart>
                            </ResponsiveContainer>
                          </ChartShell>
                        </div>
                      </AnalysisSection>

                      <AnalysisSection
                        id="Section F"
                        title="Irradiance and assumptions annex"
                        description="This section carries the assumptions and limitations that sit behind the current diagnosis, including what is and is not yet benchmarked against an external weather reference."
                        collapsed={collapsedAnalysisSections.availability}
                        onToggle={() => setCollapsedAnalysisSections((prev) => ({ ...prev, availability: !prev.availability }))}
                      >
                        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                          <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Irradiance check versus reference</p>
                            <div className="mt-4 space-y-3 text-sm leading-7 text-slate-200/84">
                              <p>
                                REVEAL now fetches ERA precipitation in-app for the performance workflow so heavy rain and potential cleaning events can be reviewed directly alongside the technical diagnosis.
                              </p>
                              <p>
                                For now, REVEAL still uses the measured irradiance series directly for PR and availability-linked interpretation, while the formal irradiance-reference correlation remains in the Long-Term workflow.
                              </p>
                              <p>
                                So the new rain context is there to support excess-soiling interpretation, but it is not yet a full in-app irradiance bankability calibration on its own.
                              </p>
                            </div>
                          </div>

                          <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Data limitations and assumptions</p>
                            <div className="mt-4 space-y-3">
                              {dataLimitations.map((line, index) => (
                                <div key={`limitation-${index}`} className="rounded-2xl border border-white/8 bg-white/5 p-4 text-sm leading-7 text-slate-200/84">
                                  {line}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </AnalysisSection>
                    </>
                  ) : analysisLaunched && isRunningAnalysis ? (
                    <div className="mt-4 rounded-[22px] border border-sky-300/20 bg-sky-400/10 p-4 text-sm leading-7 text-sky-50">
                      REVEAL is preparing the in-app diagnosis now. The KPI cards, executive summary, and punchlist will appear here automatically once the analysis finishes.
                    </div>
                  ) : assumptionsConfirmed ? (
                    <div className="mt-4 rounded-[22px] border border-violet-300/20 bg-violet-400/10 p-4 text-sm leading-7 text-violet-50">
                      Step 3 is confirmed. Hit <span className="font-semibold text-white">Launch analysis</span> above to reveal the full Step 4 diagnosis.
                    </div>
                  ) : analysisError ? (
                    <div className="mt-4 rounded-[22px] border border-amber-300/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-50">
                      REVEAL could not prepare the in-app diagnosis preview for this run. You can retry the live diagnosis or continue with the legacy export.
                      <div className="mt-4">
                        <Button variant="secondary" onClick={requestPreview} disabled={isRunningAnalysis}>
                          Retry live diagnosis
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm leading-7 text-slate-200/84">
                      REVEAL will surface the executive summary, KPIs, and improvement punchlist here once Step 3 is confirmed and the live diagnosis completes.
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <div className="rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.84)] p-5 backdrop-blur-sm">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Summary export</p>
                    <div className="mt-4 space-y-3 text-sm leading-7 text-slate-200/84">
                      <p>Use the existing PV performance-analysis engine to generate the client-ready summary export once you are happy with the live diagnosis shown in-app.</p>
                      <p>The export packages the same mapped inputs, site context, and analysis depth used in the live diagnosis. Comprehensive runs now use the full PVPAT comprehensive report path rather than the short daily-style summary.</p>
                    </div>

                    {!jobId ? (
                      <div className="mt-5">
                        <Button
                          variant="primary"
                          size="lg"
                          className="rounded-2xl"
                          loading={submitting}
                          disabled={files.length === 0 || !assumptionsConfirmed}
                          onClick={handleGenerate}
                        >
                          Generate export
                        </Button>
                      </div>
                    ) : null}
                  </div>

                  <div className="rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.84)] p-5 backdrop-blur-sm">
                    {jobId ? (
                      <>
                        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-white/48">Job progress</p>
                        <p className="mb-4 text-xs leading-6 text-white/55">Job ID {jobId}</p>
                        <ReportProgress jobId={jobId} />
                      </>
                    ) : (
                      <div className="space-y-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/48">Ready to run</p>
                        <p className="text-sm leading-7 text-slate-200/84">
                          Confirm Step 3, then launch the performance analysis. REVEAL will stream the progress here and unlock the PDF download once complete.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </WorkflowPanel>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function GenerateReportPage({ params }: { params: { siteId: string } }) {
  return (
    <Suspense fallback={<p className="px-8 py-8 text-sm text-slate-400">Loading performance workflow…</p>}>
      <GenerateReportPageContent params={params} />
    </Suspense>
  );
}
