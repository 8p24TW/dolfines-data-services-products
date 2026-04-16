"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { useDropzone } from "react-dropzone";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useColumnDetect } from "@/hooks/useAnalysis";
import { useSite } from "@/hooks/useSites";
import { api } from "@/lib/api";
import type { ColumnDetectionResult } from "@/types/analysis";
import type { LongTermCorrelationJob } from "@/types/long-term";

type SatelliteSource = "era5-land" | "era5" | "nasa-power" | "merra-2";
type OutputResolution = "10min" | "30min" | "hourly";
type OutputFormat = "csv" | "xlsx";
type TrackerMode = "fixed-tilt" | "single-axis-tracker" | "dual-axis-tracker";
type IrradianceBasis = "poa" | "ghi" | "tilted-reference";
type YieldScenario = "measured" | "p50" | "p75" | "p90";

const SITE_TIMEZONE_OPTIONS = [
  "UTC",
  "Europe/Paris",
  "Europe/London",
  "Europe/Madrid",
  "Europe/Berlin",
  "Europe/Rome",
  "Europe/Athens",
  "Africa/Casablanca",
  "Africa/Johannesburg",
  "Asia/Dubai",
  "Asia/Riyadh",
  "Asia/Kolkata",
  "Asia/Bangkok",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Perth",
  "Australia/Sydney",
  "America/Sao_Paulo",
  "America/Santiago",
  "America/Mexico_City",
  "America/Los_Angeles",
  "America/Denver",
  "America/Chicago",
  "America/New_York",
] as const;

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const;

type LongTermMapping = {
  time?: string;
  power?: string[];
  irradiance?: string;
  ambientTemperature?: string;
  moduleTemperature?: string;
  windSpeed?: string;
  windDirection?: string;
};

type ReferenceFetchResult = {
  dataset: string;
  source: string;
  siteType: string;
  cached: boolean;
  locationRequested: { latitude: number; longitude: number };
  locationUsed: { latitude: number; longitude: number };
  dateRange: { start: string; end: string };
  variables: string[];
  fileName: string;
  rowCount: number;
  columns: string[];
};

const LONG_TERM_STORAGE_VERSION = "v2";

function getLongTermStorageKey(siteId: string | number) {
  return `reveal-long-term-${LONG_TERM_STORAGE_VERSION}-${siteId}`;
}

function sanitizeLongTermMapping(value: unknown): LongTermMapping {
  if (!value || typeof value !== "object") {
    return {};
  }

  const candidate = value as Record<string, unknown>;
  return {
    time: typeof candidate.time === "string" ? candidate.time : undefined,
    power: Array.isArray(candidate.power) ? candidate.power.filter((item): item is string => typeof item === "string") : undefined,
    irradiance: typeof candidate.irradiance === "string" ? candidate.irradiance : undefined,
    ambientTemperature: typeof candidate.ambientTemperature === "string" ? candidate.ambientTemperature : undefined,
    moduleTemperature: typeof candidate.moduleTemperature === "string" ? candidate.moduleTemperature : undefined,
    windSpeed: typeof candidate.windSpeed === "string" ? candidate.windSpeed : undefined,
    windDirection: typeof candidate.windDirection === "string" ? candidate.windDirection : undefined,
  };
}

type ScreeningHeatmapCell = {
  key: string;
  label: string;
  day: number;
  status: "good" | "power" | "weather" | "both";
};

type ScreeningHeatmapMonth = {
  key: string;
  label: string;
  cells: ScreeningHeatmapCell[];
};

function parseLocalDateTime(value: string | undefined | null) {
  if (!value) return null;
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function toDateKey(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildScreeningHeatmap(summary: LongTermCorrelationJob["summary"] | null | undefined): ScreeningHeatmapMonth[] {
  if (!summary?.measuredStart || !summary?.measuredEnd) {
    return [];
  }

  const start = parseLocalDateTime(summary.measuredStart);
  const end = parseLocalDateTime(summary.measuredEnd);
  if (!start || !end || start > end) {
    return [];
  }

  const dayStatus = new Map<string, ScreeningHeatmapCell["status"]>();
  const markDate = (key: string, type: "power" | "weather") => {
    const current = dayStatus.get(key);
    dayStatus.set(
      key,
      current === "power" && type === "weather"
        ? "both"
        : current === "weather" && type === "power"
          ? "both"
          : current ?? type
    );
  };

  if (summary.badPowerDates?.length || summary.badWeatherDates?.length) {
    summary.badPowerDates?.forEach((key) => markDate(key, "power"));
    summary.badWeatherDates?.forEach((key) => markDate(key, "weather"));
  } else {
    const markWindow = (windowStart: string, windowEnd: string, type: "power" | "weather") => {
      const rangeStart = parseLocalDateTime(windowStart);
      const rangeEnd = parseLocalDateTime(windowEnd);
      if (!rangeStart || !rangeEnd) return;

      const cursor = new Date(rangeStart.getFullYear(), rangeStart.getMonth(), rangeStart.getDate());
      const finalDay = new Date(rangeEnd.getFullYear(), rangeEnd.getMonth(), rangeEnd.getDate());

      while (cursor <= finalDay) {
        markDate(toDateKey(cursor), type);
        cursor.setDate(cursor.getDate() + 1);
      }
    };

    summary.badPowerWindows?.forEach((window) => markWindow(window.start, window.end, "power"));
    summary.badWeatherWindows?.forEach((window) => markWindow(window.start, window.end, "weather"));
  }

  const months = new Map<string, ScreeningHeatmapMonth>();
  const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const finalDay = new Date(end.getFullYear(), end.getMonth(), end.getDate());

  while (cursor <= finalDay) {
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}`;
    if (!months.has(key)) {
      months.set(key, {
        key,
        label: cursor.toLocaleString("en-GB", { month: "short", year: "numeric" }),
        cells: [],
      });
    }

    months.get(key)?.cells.push({
      key: toDateKey(cursor),
      label: cursor.toLocaleDateString("en-GB"),
      day: cursor.getDate(),
      status: dayStatus.get(toDateKey(cursor)) ?? "good",
    });

    cursor.setDate(cursor.getDate() + 1);
  }

  return Array.from(months.values());
}

function isoToUk(value: string | undefined | null) {
  if (!value) return "";
  const [year, month, day] = value.slice(0, 10).split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

function ukToIso(value: string) {
  const [day, month, year] = value.split("/");
  if (!day || !month || !year) return value;
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function expectedSpecificYieldRange(latitude: number, trackerMode: TrackerMode) {
  const absLat = Math.abs(latitude);
  let lower = 950;
  let upper = 1150;

  if (absLat <= 15) {
    lower = 1550;
    upper = 1950;
  } else if (absLat <= 25) {
    lower = 1450;
    upper = 1850;
  } else if (absLat <= 35) {
    lower = 1300;
    upper = 1700;
  } else if (absLat <= 45) {
    lower = 1100;
    upper = 1500;
  } else if (absLat <= 55) {
    lower = 900;
    upper = 1250;
  }

  const trackerFactor = trackerMode === "single-axis-tracker" ? 1.12 : trackerMode === "dual-axis-tracker" ? 1.18 : 1.0;
  return {
    lower: Math.round(lower * trackerFactor),
    upper: Math.round(upper * trackerFactor),
  };
}

function FieldLabel({ children }: { children: ReactNode }) {
  return <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-white/55">{children}</label>;
}

function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.92)] px-4 py-3 text-sm font-medium text-white outline-none transition placeholder:text-slate-500 focus:border-orange-DEFAULT ${
        props.className ?? ""
      }`}
    />
  );
}

function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.92)] px-4 py-3 text-sm font-medium text-white outline-none transition focus:border-orange-DEFAULT ${
        props.className ?? ""
      }`}
    />
  );
}

function stepCardClass(tone: "sky" | "emerald" | "amber" | "teal" | "violet", highlighted: boolean) {
  const base = {
    sky: "border-sky-300/20 bg-[linear-gradient(180deg,rgba(56,189,248,0.18),rgba(8,47,73,0.24))]",
    emerald: "border-emerald-300/20 bg-[linear-gradient(180deg,rgba(52,211,153,0.18),rgba(6,46,34,0.24))]",
    amber: "border-amber-300/20 bg-[linear-gradient(180deg,rgba(251,191,36,0.18),rgba(69,26,3,0.24))]",
    teal: "border-teal-300/20 bg-[linear-gradient(180deg,rgba(45,212,191,0.18),rgba(19,78,74,0.24))]",
    violet: "border-violet-300/20 bg-[linear-gradient(180deg,rgba(196,181,253,0.18),rgba(46,16,101,0.24))]",
  }[tone];
  const glow = highlighted ? " workflow-step-glow ring-2 ring-white/35 shadow-[0_0_0_1px_rgba(255,255,255,0.12),0_0_42px_rgba(255,255,255,0.2)]" : "";
  return `rounded-[24px] border p-4 transition-all duration-300 ${base}${glow}`;
}

function workflowPanelClass(tone: "sky" | "emerald" | "amber" | "teal" | "violet", highlighted: boolean) {
  const base = {
    sky: "border-sky-300/18 bg-[linear-gradient(180deg,rgba(56,189,248,0.12),rgba(8,47,73,0.18))]",
    emerald: "border-emerald-300/18 bg-[linear-gradient(180deg,rgba(52,211,153,0.12),rgba(6,46,34,0.18))]",
    amber: "border-amber-300/18 bg-[linear-gradient(180deg,rgba(251,191,36,0.12),rgba(69,26,3,0.18))]",
    teal: "border-teal-300/18 bg-[linear-gradient(180deg,rgba(45,212,191,0.12),rgba(19,78,74,0.18))]",
    violet: "border-violet-300/18 bg-[linear-gradient(180deg,rgba(196,181,253,0.12),rgba(46,16,101,0.18))]",
  }[tone];
  const glow = highlighted ? " workflow-step-glow ring-2 ring-white/30 shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_0_42px_rgba(255,255,255,0.18)]" : "";
  return `rounded-[28px] border px-5 py-4 backdrop-blur-sm transition-all duration-300 ${base}${glow}`;
}

function WorkflowPanel({
  step,
  title,
  description,
  tone,
  highlighted,
  collapsed,
  onToggle,
  summary,
  children,
}: {
  step: string;
  title: string;
  description: string;
  tone: "sky" | "emerald" | "amber" | "teal" | "violet";
  highlighted: boolean;
  collapsed: boolean;
  onToggle: () => void;
  summary?: string;
  children: ReactNode;
}) {
  return (
    <section className={workflowPanelClass(tone, highlighted)}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/60">{step}</p>
            <h2 className="font-dolfines text-2xl font-semibold tracking-[0.04em] text-white">{title}</h2>
            <p className="max-w-5xl text-sm leading-7 text-slate-200/82 lg:whitespace-nowrap lg:overflow-hidden lg:text-ellipsis">{description}</p>
            {summary ? <p className="text-xs leading-6 text-slate-400/90 lg:whitespace-nowrap lg:overflow-hidden lg:text-ellipsis">{summary}</p> : null}
          </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-full border border-white/12 bg-white/6 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/10"
        >
          {collapsed ? "Expand details" : "Collapse details"}
        </button>
      </div>
      {collapsed ? null : <div className="mt-4">{children}</div>}
    </section>
  );
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
      <div className="mb-5">
        <h2 className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">{title}</h2>
        {subtitle ? <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-200/82">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

function inferColumn(columns: string[], patterns: string[]) {
  const lower = columns.map((column) => ({ original: column, lower: column.toLowerCase() }));
  for (const pattern of patterns) {
    const found = lower.find((column) => column.lower.includes(pattern));
    if (found) return found.original;
  }
  return "";
}

function inferLongTermMapping(
  siteType: "solar" | "wind",
  detection: ColumnDetectionResult
): LongTermMapping {
  const columns = detection.columns ?? [];
  const mapping = detection.mapping ?? {};

  if (siteType === "solar") {
    return {
      time: mapping.time ?? inferColumn(columns, ["timestamp", "date", "time"]),
      power:
        Array.isArray(mapping.power) && mapping.power.length > 0
          ? mapping.power
          : columns.filter((column) => /ond|inv|inverter|pac|p_ac|power|puissance|kw|mw|pout/i.test(column)),
      irradiance:
        mapping.irradiance ??
        inferColumn(columns, ["irr", "irradiance", "poa", "ghi", "pyr", "sat"]),
      ambientTemperature: inferColumn(columns, ["ambient", "wstext", "temp ext", "outside temp", "ta"]),
      moduleTemperature: inferColumn(columns, ["module", "panel", "panneau", "cell temp", "tmod"]),
    };
  }

  return {
    time: mapping.time ?? inferColumn(columns, ["timestamp", "date", "time"]),
    power: Array.isArray(mapping.power) ? mapping.power : [],
    windSpeed: mapping.wind_speed ?? inferColumn(columns, ["wind speed", "windspeed", "ws", "speed"]),
    windDirection: mapping.wind_dir ?? inferColumn(columns, ["wind direction", "winddir", "direction", "wd"]),
    ambientTemperature:
      mapping.temperature ?? inferColumn(columns, ["ambient", "temperature", "temp", "outside"]),
  };
}

function MappingSelect({
  label,
  value,
  headers,
  onChange,
}: {
  label: string;
  value: string;
  headers: string[];
  onChange: (next: string) => void;
}) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <SelectInput value={value} onChange={(event) => onChange(event.currentTarget.value)}>
        <option value="">Not used</option>
        {headers.map((header) => (
          <option key={header} value={header}>
            {header}
          </option>
        ))}
      </SelectInput>
    </div>
  );
}

function PowerChecklist({
  headers,
  selected,
  onChange,
  collapsed,
  onToggleCollapsed,
}: {
  headers: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  function toggle(header: string) {
    if (selected.includes(header)) {
      onChange(selected.filter((item) => item !== header));
      return;
    }
    onChange([...selected, header]);
  }

  function selectAll() {
    onChange([...headers]);
  }

  function clearAll() {
    onChange([]);
  }

  return (
    <div>
      <FieldLabel>Power channels</FieldLabel>
      <div className="rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.92)] p-3">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-300/80">Tick the inverter, junction-box, or turbine channels to aggregate in the long-term model.</p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="rounded-full border border-white/10 bg-white/8 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/12"
            >
              {collapsed ? "Expand" : "Collapse"}
            </button>
            <button
              type="button"
              onClick={selectAll}
              className="rounded-full border border-white/10 bg-white/8 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/12"
            >
              Select all
            </button>
            <button
              type="button"
              onClick={clearAll}
              className="rounded-full border border-white/10 bg-white/8 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/12"
            >
              Clear
            </button>
            <span className="rounded-full border border-orange-DEFAULT/20 bg-orange-DEFAULT/12 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-orange-100">
              {selected.length} selected
            </span>
          </div>
        </div>
        {collapsed ? null : (
          <div className="grid max-h-[18rem] grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
            {headers.map((header) => {
              const active = selected.includes(header);
              return (
                <button
                  key={header}
                  type="button"
                  onClick={() => toggle(header)}
                  className={`flex items-center gap-3 rounded-2xl border px-3 py-2 text-left text-sm transition ${
                    active
                      ? "border-orange-DEFAULT bg-orange-DEFAULT/18 text-white"
                      : "border-white/10 bg-white/5 text-slate-200 hover:border-white/25 hover:bg-white/8"
                  }`}
                >
                  <span
                    className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] ${
                      active ? "border-orange-100 bg-orange-DEFAULT text-white" : "border-white/30 text-transparent"
                    }`}
                  >
                    ✓
                  </span>
                  <span className="truncate">{header}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default function LongTermModellingPage({ params }: { params: { siteId: string } }) {
  const { site, isLoading } = useSite(params.siteId);
  const { trigger: detectColumns, isMutating: isDetecting } = useColumnDetect();
  const [files, setFiles] = useState<File[]>([]);
  const [detections, setDetections] = useState<Record<string, ColumnDetectionResult>>({});
  const [columnMappings, setColumnMappings] = useState<Record<string, LongTermMapping>>({});
  const [collapsedPowerLists, setCollapsedPowerLists] = useState<Record<string, boolean>>({});
  const [collapsedSteps, setCollapsedSteps] = useState<Record<number, boolean>>({ 2: true, 3: true, 4: true, 5: true });
  const [detectionProgress, setDetectionProgress] = useState(0);
  const [detectionProgressLabel, setDetectionProgressLabel] = useState("");
  const [setupSaved, setSetupSaved] = useState(false);
  const [hasSavedSetup, setHasSavedSetup] = useState(false);
  const [referenceMessage, setReferenceMessage] = useState("");
  const [referenceFetchResult, setReferenceFetchResult] = useState<ReferenceFetchResult | null>(null);
  const [fetchingReference, setFetchingReference] = useState(false);
  const [longTermJob, setLongTermJob] = useState<LongTermCorrelationJob | null>(null);
  const [startingLongTermJob, setStartingLongTermJob] = useState(false);
  const [startingRunMode, setStartingRunMode] = useState<LongTermCorrelationJob["runMode"]>();
  const [runMessage, setRunMessage] = useState("");
  const [satelliteSource, setSatelliteSource] = useState<SatelliteSource>("era5-land");
  const [correlationYears, setCorrelationYears] = useState("20");
  const [outputResolution, setOutputResolution] = useState<OutputResolution>("hourly");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("csv");
  const [actualDataStartDate, setActualDataStartDate] = useState("01/01/2023");
  const [actualDataEndDate, setActualDataEndDate] = useState("31/12/2024");
  const [referenceFetchProgress, setReferenceFetchProgress] = useState(0);
  const [trackerMode, setTrackerMode] = useState<TrackerMode>("fixed-tilt");
  const [irradianceBasis, setIrradianceBasis] = useState<IrradianceBasis>("poa");
  const [irradianceTiltDeg, setIrradianceTiltDeg] = useState("");
  const [moduleTiltDeg, setModuleTiltDeg] = useState("");
  const [dcCapacity, setDcCapacity] = useState("");
  const [acCapacity, setAcCapacity] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [siteTimezone, setSiteTimezone] = useState("Europe/Paris");
  const [confirmedTimezone, setConfirmedTimezone] = useState("");
  const [yieldScenario, setYieldScenario] = useState<YieldScenario>("measured");
  const [specificYieldInput, setSpecificYieldInput] = useState("");
  const [latestScreeningSummary, setLatestScreeningSummary] = useState<LongTermCorrelationJob["summary"] | null>(null);
  const [latestPreviewSummary, setLatestPreviewSummary] = useState<LongTermCorrelationJob["summary"] | null>(null);
  const [lastScreeningSignature, setLastScreeningSignature] = useState("");
  const [lastPreviewSignature, setLastPreviewSignature] = useState("");
  const [confirmedYieldSignature, setConfirmedYieldSignature] = useState("");

  const isSolar = site?.site_type === "solar";

  useEffect(() => {
    if (!site) return;
    setDcCapacity((previous) => previous || String(site.cap_dc_kwp || ""));
    setAcCapacity((previous) => previous || String(site.cap_ac_kw || ""));
    setLatitude((previous) => previous || String(site.lat ?? ""));
    setLongitude((previous) => previous || String(site.lon ?? ""));
    if (isSolar) {
      setModuleTiltDeg((previous) => previous || "22");
      setIrradianceTiltDeg((previous) => previous || "22");
      setTrackerMode((previous) => previous || "fixed-tilt");
      setIrradianceBasis((previous) => previous || "poa");
    }
  }, [site, isSolar]);

  useEffect(() => {
    if (!site) return;

    try {
      const raw = window.localStorage.getItem(getLongTermStorageKey(site.id));
      if (!raw) return;

      const saved = JSON.parse(raw) as {
        dcCapacity?: string;
        acCapacity?: string;
        latitude?: string;
        longitude?: string;
        siteTimezone?: string;
        confirmedTimezone?: string;
        yieldScenario?: YieldScenario;
        specificYieldInput?: string;
        lastScreeningSignature?: string;
        trackerMode?: TrackerMode;
        irradianceBasis?: IrradianceBasis;
        moduleTiltDeg?: string;
        irradianceTiltDeg?: string;
        satelliteSource?: SatelliteSource;
        correlationYears?: string;
        outputResolution?: OutputResolution;
        outputFormat?: OutputFormat;
        actualDataStartDate?: string;
        actualDataEndDate?: string;
        columnMappings?: Record<string, LongTermMapping>;
        lastPreviewSignature?: string;
        confirmedYieldSignature?: string;
      };

      const safeColumnMappings =
        saved.columnMappings && typeof saved.columnMappings === "object"
          ? Object.fromEntries(
              Object.entries(saved.columnMappings).map(([filename, mapping]) => [filename, sanitizeLongTermMapping(mapping)])
            )
          : undefined;

      if (saved.dcCapacity) setDcCapacity(saved.dcCapacity);
      if (saved.acCapacity) setAcCapacity(saved.acCapacity);
      if (saved.latitude) setLatitude(saved.latitude);
      if (saved.longitude) setLongitude(saved.longitude);
      if (saved.siteTimezone) setSiteTimezone(saved.siteTimezone);
      if (saved.confirmedTimezone) setConfirmedTimezone(saved.confirmedTimezone);
      if (saved.yieldScenario) setYieldScenario(saved.yieldScenario);
      if (saved.specificYieldInput) setSpecificYieldInput(saved.specificYieldInput);
      if (saved.lastScreeningSignature) setLastScreeningSignature(saved.lastScreeningSignature);
      if (saved.satelliteSource) setSatelliteSource(saved.satelliteSource);
      if (saved.correlationYears) setCorrelationYears(saved.correlationYears);
      if (saved.outputResolution) setOutputResolution(saved.outputResolution);
      if (saved.outputFormat) setOutputFormat(saved.outputFormat);
      if (saved.actualDataStartDate) setActualDataStartDate(saved.actualDataStartDate);
      if (saved.actualDataEndDate) setActualDataEndDate(saved.actualDataEndDate);
      if (safeColumnMappings) setColumnMappings(safeColumnMappings);
      if (saved.lastPreviewSignature) setLastPreviewSignature(saved.lastPreviewSignature);
      if (saved.confirmedYieldSignature) setConfirmedYieldSignature(saved.confirmedYieldSignature);
      setHasSavedSetup(true);

      if (isSolar) {
        if (saved.trackerMode) setTrackerMode(saved.trackerMode);
        if (saved.irradianceBasis) setIrradianceBasis(saved.irradianceBasis);
        if (saved.moduleTiltDeg) setModuleTiltDeg(saved.moduleTiltDeg);
        if (saved.irradianceTiltDeg) setIrradianceTiltDeg(saved.irradianceTiltDeg);
      }
    } catch {
      // Ignore invalid local storage payloads and fall back to site defaults.
    }
  }, [site, isSolar]);

  useEffect(() => {
    if (!longTermJob || !["queued", "running"].includes(longTermJob.status)) return;

    const timer = window.setInterval(async () => {
      try {
        const nextJob = await api.longTerm.getJob(longTermJob.jobId);
        setLongTermJob(nextJob);
      } catch (error) {
        setRunMessage(error instanceof Error ? error.message : "Failed to refresh long-term job status.");
        window.clearInterval(timer);
      }
    }, 1200);

    return () => window.clearInterval(timer);
  }, [longTermJob]);

  useEffect(() => {
    if (longTermJob?.status === "complete" && longTermJob.runMode === "screening") {
      setLatestScreeningSummary(longTermJob.summary ?? null);
    }
  }, [longTermJob]);

  useEffect(() => {
    if (longTermJob?.status === "complete" && longTermJob.runMode === "preview") {
      setLatestPreviewSummary(longTermJob.summary ?? null);
    }
  }, [longTermJob]);

  useEffect(() => {
    if (!isDetecting) {
      if (detectionProgress > 0) {
        setDetectionProgress(100);
        const finishTimer = window.setTimeout(() => {
          setDetectionProgress(0);
          setDetectionProgressLabel("");
        }, 700);
        return () => window.clearTimeout(finishTimer);
      }
      return;
    }

    if (!detectionProgressLabel) {
      setDetectionProgressLabel("Analysing uploaded file structure");
    }

    const timer = window.setInterval(() => {
      setDetectionProgress((current) => Math.min(current + (current < 60 ? 9 : current < 85 ? 4 : 1), 92));
    }, 350);

    return () => window.clearInterval(timer);
  }, [isDetecting, detectionProgress, detectionProgressLabel]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!site || acceptedFiles.length === 0) return;

      setFiles(acceptedFiles);
      setDetections({});
      setColumnMappings({});
      setCollapsedPowerLists({});
      setReferenceFetchResult(null);
      setLongTermJob(null);
      setLatestScreeningSummary(null);
      setLatestPreviewSummary(null);
      setLastScreeningSignature("");
      setLastPreviewSignature("");
      setConfirmedYieldSignature("");
      setDetectionProgress(8);
      setDetectionProgressLabel(
        acceptedFiles.length === 1
          ? `Analysing ${acceptedFiles[0]?.name ?? "uploaded file"}`
          : `Analysing ${acceptedFiles.length} uploaded files`
      );

      const nextDetections = await Promise.all(
        acceptedFiles.map(async (file) => {
          const form = new FormData();
          form.append("file", file, file.name);
          form.append("siteType", site.site_type);
          const detection = await detectColumns(form);
          return [file.name, detection] as const;
        })
      );

      setDetections((previous) => {
        const merged = { ...previous, ...Object.fromEntries(nextDetections) };
        setColumnMappings((current) => {
          const nextMappings = { ...current };
          for (const [filename, detection] of nextDetections) {
            nextMappings[filename] = inferLongTermMapping(site.site_type, detection);
          }
          return nextMappings;
        });
        return merged;
      });

      const detectedRanges = nextDetections
        .map(([, detection]) => detection.data_date_range)
        .filter((range): range is [string, string] => Array.isArray(range) && range.length === 2);

      if (detectedRanges.length > 0) {
        const starts = detectedRanges.map((range) => range[0]).sort();
        const ends = detectedRanges.map((range) => range[1]).sort();
        setActualDataStartDate(isoToUk(starts[0] ?? ""));
        setActualDataEndDate(isoToUk(ends[ends.length - 1] ?? ""));
      }
    },
    [detectColumns, site]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".xls", ".xlsx"],
    },
    multiple: true,
  });

  const currentSite = site;
  const firstFileName = files[0]?.name;
  const firstFileMapping = firstFileName ? sanitizeLongTermMapping(columnMappings[firstFileName]) : undefined;
  const yieldConfirmationSignature = JSON.stringify({
    yieldScenario,
    specificYieldInput,
    dcCapacity,
    latitude,
    longitude,
    siteTimezone,
    trackerMode: isSolar ? trackerMode : "n/a",
    actualDataStartDate,
    actualDataEndDate,
    files: files.map((file) => file.name).sort(),
    mapping: firstFileName
      ? {
          time: firstFileMapping?.time ?? "",
          power: (firstFileMapping?.power ?? []).slice().sort(),
          irradiance: firstFileMapping?.irradiance ?? "",
        }
      : null,
  });
  const screeningSignature = JSON.stringify({
    siteTimezone,
    files: files.map((file) => file.name).sort(),
    mapping: firstFileName
      ? {
          time: firstFileMapping?.time ?? "",
          power: (firstFileMapping?.power ?? []).slice().sort(),
        }
      : null,
  });
  const isTimezoneConfirmed = confirmedTimezone === siteTimezone;
  const hasCurrentScreening = lastScreeningSignature === screeningSignature && Boolean(latestScreeningSummary);
  const hasCurrentPreview = lastPreviewSignature === yieldConfirmationSignature && Boolean(latestPreviewSummary);
  const isSpecificYieldConfirmed = confirmedYieldSignature === yieldConfirmationSignature && hasCurrentPreview;
  const measuredSpecificYieldDisplay =
    yieldScenario === "measured" && latestPreviewSummary?.measuredSpecificYieldKwhKwp != null
      ? String(latestPreviewSummary.measuredSpecificYieldKwhKwp)
      : specificYieldInput;
  const hasAnalysedFiles =
    files.length > 0 && !isDetecting && files.every((file) => Boolean(detections[file.name]));
  const canConfirmSpecificYield = Boolean(referenceFetchResult) && !fetchingReference && files.length > 0;
  const canRunLongTermCorrelation = Boolean(referenceFetchResult) && !fetchingReference && isSpecificYieldConfirmed;
  const showRunNextPrompt = Boolean(referenceFetchResult) && !fetchingReference && (!longTermJob || longTermJob.runMode !== "projection");
  const latitudeNumber = Number(latitude);
  const yieldBenchmark =
    Number.isFinite(latitudeNumber) && isSolar
      ? expectedSpecificYieldRange(latitudeNumber, trackerMode)
      : null;
  const lowSpecificYieldWarning =
    longTermJob?.summary?.measuredSpecificYieldKwhKwp != null && yieldBenchmark
      ? longTermJob.summary.measuredSpecificYieldKwhKwp < yieldBenchmark.lower * 0.9
      : false;
  const limitedFullYearsWarning =
    longTermJob?.summary?.fullMeasuredYears != null
      ? longTermJob.summary.fullMeasuredYears < 3
      : false;
  const highlightedStep =
    !hasAnalysedFiles ? 1 : !hasSavedSetup || !referenceFetchResult ? 2 : !hasCurrentScreening ? 3 : !hasCurrentPreview ? 4 : 5;
  const visibleScreeningSummary =
    longTermJob?.status === "complete" && longTermJob.runMode === "screening"
      ? longTermJob.summary
      : latestScreeningSummary;
  const screeningHeatmapMonths = buildScreeningHeatmap(visibleScreeningSummary);
  const annualChartData =
    longTermJob?.charts?.annualEnergy?.reduce<Array<{ label: string; actual: number; projected: number; referenceIrradiation: number }>>((acc, row) => {
      const key = String(row.year ?? "");
      let entry = acc.find((item) => item.label === key);
      if (!entry) {
        entry = { label: key, actual: 0, projected: 0, referenceIrradiation: 0 };
        acc.push(entry);
      }
      if (row.mode === "actual") {
        entry.actual = row.energy_mwh;
      } else if (row.mode === "projected") {
        entry.projected = row.energy_mwh;
      } else if (row.mode === "reference") {
        entry.referenceIrradiation = row.irradiation_kwh_m2 ?? 0;
      }
      return acc;
    }, []) ?? [];

  const monthlyChartData =
    longTermJob?.charts?.monthlyEnergy?.reduce<Array<{ label: string; actual: number; projected: number; referenceIrradiation: number }>>((acc, row) => {
      const monthNumber = Number(row.month ?? 0);
      const key = MONTH_LABELS[Math.max(0, Math.min(11, monthNumber - 1))] ?? `${String(row.month ?? "").padStart(2, "0")}`;
      let entry = acc.find((item) => item.label === key);
      if (!entry) {
        entry = { label: key, actual: 0, projected: 0, referenceIrradiation: 0 };
        acc.push(entry);
      }
      if (row.mode === "actual") {
        entry.actual = row.energy_mwh;
      } else if (row.mode === "projected") {
        entry.projected = row.energy_mwh;
      } else if (row.mode === "reference") {
        entry.referenceIrradiation = row.irradiation_kwh_m2 ?? 0;
      }
      return acc;
    }, []) ?? [];
  const irradianceFitData = longTermJob?.charts?.irradianceFit ?? [];
  const fitXValues = irradianceFitData.map((point) => point.reference_irradiance_kwh_m2);
  const fitLineSegment =
    fitXValues.length > 0 && longTermJob?.summary?.irradianceFitSlope != null && longTermJob?.summary?.irradianceFitIntercept != null
      ? [
          {
            x: Math.min(...fitXValues),
            y:
              Math.min(...fitXValues) * longTermJob.summary.irradianceFitSlope +
              longTermJob.summary.irradianceFitIntercept,
          },
          {
            x: Math.max(...fitXValues),
            y:
              Math.max(...fitXValues) * longTermJob.summary.irradianceFitSlope +
              longTermJob.summary.irradianceFitIntercept,
          },
        ]
      : null;

  useEffect(() => {
    setCollapsedSteps((previous) => ({ ...previous, [highlightedStep]: false }));
  }, [highlightedStep]);

  if (isLoading || !currentSite) {
    return <p className="px-8 py-8 text-sm text-slate-400">Loading long-term modelling workspace…</p>;
  }

  function handleSaveSetup() {
      if (!currentSite) return;
      const payload = {
        siteId: currentSite.id,
        siteType: currentSite.site_type,
        dcCapacity,
        acCapacity,
        latitude,
        longitude,
        siteTimezone,
        confirmedTimezone,
        yieldScenario,
        specificYieldInput,
        lastScreeningSignature,
        trackerMode: isSolar ? trackerMode : undefined,
        irradianceBasis: isSolar ? irradianceBasis : undefined,
        moduleTiltDeg: isSolar ? moduleTiltDeg : undefined,
        irradianceTiltDeg: isSolar ? irradianceTiltDeg : undefined,
        satelliteSource,
        correlationYears,
        outputResolution,
        outputFormat,
        actualDataStartDate,
        actualDataEndDate,
        columnMappings,
        lastPreviewSignature,
        confirmedYieldSignature,
        savedAt: new Date().toISOString(),
      };

    window.localStorage.setItem(getLongTermStorageKey(currentSite.id), JSON.stringify(payload));
    setSetupSaved(true);
    setHasSavedSetup(true);
    window.setTimeout(() => setSetupSaved(false), 3000);
  }

  function handleConfirmTimezone() {
    setConfirmedTimezone(siteTimezone);
    setRunMessage(`Timezone confirmed. REVEAL will align the measured SCADA timestamps using ${siteTimezone} before correlating against ERA UTC data.`);
  }

  async function handleFetchReferenceWeather() {
    if (!currentSite) return;
    let progressTimer: number | undefined;
    setFetchingReference(true);
    setReferenceFetchProgress(12);
    setReferenceMessage("");
    try {
      progressTimer = window.setInterval(() => {
        setReferenceFetchProgress((current) => Math.min(current + 8, 88));
      }, 700);

      const form = new FormData();
      form.append("source", satelliteSource);
      form.append("site_type", currentSite.site_type);
      form.append("latitude", latitude);
      form.append("longitude", longitude);
      form.append("start_date", ukToIso(actualDataStartDate));
      form.append("end_date", ukToIso(actualDataEndDate));

      const result = await api.longTerm.fetchReference(form);
      setReferenceFetchProgress(100);
      setReferenceFetchResult(result);
      setReferenceMessage(
        `Reference weather fetched successfully from ${result.dataset} for ${result.dateRange.start} to ${result.dateRange.end}. Next step: run the bad-data screen, then analyse the fit and yield.`
      );
    } catch (error) {
      setReferenceFetchResult(null);
      setReferenceMessage(error instanceof Error ? error.message : "Failed to fetch reference weather.");
    } finally {
      if (progressTimer) {
        window.clearInterval(progressTimer);
      }
      setFetchingReference(false);
    }
  }

  async function startLongTermRun(runMode: "screening" | "preview" | "projection") {
    if (!currentSite) return;
    if (files.length === 0) {
      setRunMessage("Please upload and confirm a measured SCADA file before starting the long-term workflow.");
      return;
    }

    const firstFile = files[0];
    const firstMapping = columnMappings[firstFile.name];
    if (!firstMapping?.time || !firstMapping?.power?.length || !(isSolar ? firstMapping?.irradiance : firstMapping?.windSpeed)) {
      setRunMessage("Please confirm the timestamp, power channels, and resource columns before starting the run.");
      return;
    }
    if (yieldScenario !== "measured" && (!specificYieldInput || Number(specificYieldInput) <= 0)) {
      setRunMessage("Please enter a valid specific-yield input before running a custom P50/P75/P90 projection.");
      return;
    }
    if (!isTimezoneConfirmed) {
      setRunMessage("Please confirm the site timezone before continuing so REVEAL can align the site timestamps with the ERA UTC reference.");
      return;
    }
    if ((runMode === "preview" || runMode === "projection") && !hasCurrentScreening) {
      setRunMessage("Please run the bad-data screen first so REVEAL can exclude flatlined power periods before the fit and projection steps.");
      return;
    }
    if (runMode === "projection" && !isSpecificYieldConfirmed) {
      setRunMessage("Please confirm the specific-yield basis after reviewing the fit and yield results before generating the long-term output file.");
      return;
    }

      setStartingLongTermJob(true);
      setStartingRunMode(runMode);
      setRunMessage("");
    try {
      if (runMode === "screening") {
        setLastScreeningSignature("");
        setLatestScreeningSummary(null);
        setLatestPreviewSummary(null);
        setConfirmedYieldSignature("");
        setLastPreviewSignature("");
      }

      if (runMode === "preview") {
        setLatestPreviewSummary(null);
        setConfirmedYieldSignature("");
        setLastPreviewSignature("");
      }

      const form = new FormData();
      form.append("siteId", currentSite.id);
      form.append("siteType", currentSite.site_type);
      form.append("source", satelliteSource);
      form.append("latitude", latitude);
      form.append("longitude", longitude);
      form.append("siteTimezone", siteTimezone);
      form.append("startDate", ukToIso(actualDataStartDate));
      form.append("endDate", ukToIso(actualDataEndDate));
      form.append("correlationYears", correlationYears);
      form.append("dcCapacityKwp", dcCapacity);
      form.append("acCapacityKw", acCapacity);
      form.append("specificYieldKwhKwp", yieldScenario === "measured" ? "0" : specificYieldInput);
      form.append("yieldScenario", yieldScenario);
      form.append("runMode", runMode);
      form.append("irradianceBasis", irradianceBasis);
      form.append("trackerMode", trackerMode);
      form.append("irradianceTiltDeg", irradianceTiltDeg || moduleTiltDeg || "0");
      form.append("outputFormat", outputFormat);
      form.append("columnMappings", JSON.stringify(firstMapping));
      files.forEach((file) => form.append("files", file, file.name));

      const response = await api.longTerm.createJob(form);
      if (runMode === "screening") {
        setLastScreeningSignature(screeningSignature);
      }
      if (runMode === "preview") {
        setLastPreviewSignature(yieldConfirmationSignature);
      }
      setLongTermJob({
        jobId: response.jobId,
        siteId: currentSite.id,
        runMode,
        status: "queued",
        progress: 0,
        stage: "Queued",
        outputFormat,
      });
    } catch (error) {
      setRunMessage(error instanceof Error ? error.message : "Failed to start long-term correlation.");
    } finally {
      setStartingLongTermJob(false);
      setStartingRunMode(undefined);
    }
  }

  async function handleAnalyseFitAndYield() {
    await startLongTermRun("preview");
  }

  async function handleScreenBadData() {
    await startLongTermRun("screening");
  }

  async function handleRunLongTermCorrelation() {
    await startLongTermRun("projection");
  }

  function handleConfirmSpecificYield() {
    if (yieldScenario !== "measured" && (!specificYieldInput || Number(specificYieldInput) <= 0)) {
      setRunMessage("Please enter a valid specific-yield input before confirming a custom P50/P75/P90 projection.");
      return;
    }

    if (!referenceFetchResult) {
      setRunMessage("Fetch the reference weather first so REVEAL can prepare the yield review step.");
      return;
    }

    if (files.length === 0) {
      setRunMessage("Upload and confirm a measured SCADA file before confirming the specific-yield basis.");
      return;
    }

    if (!hasCurrentPreview) {
      setRunMessage("Run the fit-and-yield review first so REVEAL can show the irradiance fit, regression, and yield metrics before confirmation.");
      return;
    }

    setConfirmedYieldSignature(yieldConfirmationSignature);
    setRunMessage(
      yieldScenario === "measured"
        ? "Specific yield confirmed. REVEAL will use the measured yield basis when generating the long-term output file."
        : `Specific yield confirmed. REVEAL will use the custom ${yieldScenario.toUpperCase()} yield basis when generating the long-term output file.`
    );
  }

  function toggleStep(step: number) {
    setCollapsedSteps((previous) => ({ ...previous, [step]: !previous[step] }));
  }

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
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.9),rgba(4,24,36,0.8),rgba(4,24,36,0.7))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href={`/dashboard/site/${currentSite.id}`} label="Back to site" />

        <section className="rounded-[28px] border border-white/10 bg-[rgba(3,16,26,0.78)] p-6 backdrop-blur-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
              <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">
                Long-Term Modelling · {currentSite.display_name}
              </h1>
              <p className="max-w-4xl text-sm leading-7 text-slate-200/82">
                Upload the measured data, confirm the site assumptions and reference weather, screen bad data, review the fit and yield,
                then confirm the yield basis before downloading the long-term output.
              </p>
            </div>
            <Link href="/dashboard/knowledge-base">
              <Button variant="secondary">Open Resource Database</Button>
            </Link>
          </div>
        </section>

        <WorkflowPanel
          step="Step 1"
          title="Upload actual data"
          description="Drop the measured SCADA workbook here, let REVEAL analyse the structure, and confirm the detected columns before the long-term workflow continues."
          tone="sky"
          highlighted={highlightedStep === 1}
          collapsed={collapsedSteps[1] ?? false}
          onToggle={() => toggleStep(1)}
          summary={hasAnalysedFiles ? `${files.length} measured file${files.length === 1 ? "" : "s"} analysed and ready for mapping.` : "Upload a measured file to begin the long-term workflow."}
        >
          <div
            {...getRootProps()}
            className={`rounded-[26px] border-2 border-dashed p-8 text-center transition ${
              isDragActive
                ? "border-orange-DEFAULT bg-orange-DEFAULT/12"
                : "border-white/18 bg-[rgba(255,255,255,0.04)] hover:border-orange-DEFAULT/50"
            }`}
          >
            <input {...getInputProps()} />
            <p className="text-base font-semibold text-white">
              {isDragActive ? "Drop the long-term SCADA file here" : "Drag & drop the measured SCADA workbook, or click to browse"}
            </p>
            <p className="mt-2 text-sm text-slate-300/78">Accepted formats: CSV, XLS, XLSX. Column detection runs automatically after upload, and a new upload replaces the previous long-term source file.</p>
          </div>

          {files.length > 0 ? (
            <div className="mt-5 space-y-3">
              {files.map((file) => (
                <div key={file.name} className="rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.9)] px-4 py-3 text-sm text-slate-100">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{file.name}</p>
                      <p className="text-xs text-slate-400">
                        {detections[file.name]?.row_count
                          ? `${detections[file.name]?.row_count.toLocaleString()} rows detected`
                          : "Waiting for detection"}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setFiles((previous) => previous.filter((entry) => entry.name !== file.name));
                        setDetections((previous) => {
                          const next = { ...previous };
                          delete next[file.name];
                          return next;
                        });
                        setColumnMappings((previous) => {
                          const next = { ...previous };
                          delete next[file.name];
                          return next;
                        });
                        setCollapsedPowerLists((previous) => {
                          const next = { ...previous };
                          delete next[file.name];
                          return next;
                        });
                      }}
                      className="text-sm font-semibold text-slate-300 transition hover:text-white"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {files.length > 0 ? (
            <div className="mt-4 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Measured data analysis</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                    {isDetecting ? detectionProgressLabel || "Analysing uploaded file" : "Column analysis complete"}
                  </p>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                  {isDetecting ? `${detectionProgress}%` : "100%"}
                </div>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(88,176,255,0.96),rgba(125,211,252,0.96))] transition-all duration-500"
                  style={{ width: `${isDetecting ? detectionProgress : 100}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-slate-300/84">
                {isDetecting
                  ? "REVEAL is scanning the CSV/XLSX structure, proposing column roles, and detecting the measured date range."
                  : "Columns detected. Please review and confirm the mappings below before moving to the site assumptions and reference settings."}
              </p>
            </div>
          ) : null}

          {files.map((file) => {
            const detection = detections[file.name];
            const headers = detection?.columns ?? [];
            const mapping = columnMappings[file.name] ?? {};

            if (!detection) return null;

            return (
              <div key={`${file.name}-mapping`} className="mt-5 rounded-[24px] border border-white/10 bg-[rgba(5,20,32,0.92)] p-5">
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-100/70">Detected file</p>
                    <h3 className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">{file.name}</h3>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-200">
                    {headers.length} columns found
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <MappingSelect
                    label="Timestamp"
                    value={mapping.time ?? ""}
                    headers={headers}
                    onChange={(value) =>
                      setColumnMappings((previous) => ({
                        ...previous,
                        [file.name]: { ...previous[file.name], time: value },
                      }))
                    }
                  />
                  {isSolar ? (
                    <MappingSelect
                      label="Irradiance"
                      value={mapping.irradiance ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], irradiance: value },
                        }))
                      }
                    />
                  ) : (
                    <MappingSelect
                      label="Wind speed"
                      value={mapping.windSpeed ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], windSpeed: value },
                        }))
                      }
                    />
                  )}
                  {isSolar ? (
                    <MappingSelect
                      label="Ambient temperature"
                      value={mapping.ambientTemperature ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], ambientTemperature: value },
                        }))
                      }
                    />
                  ) : (
                    <MappingSelect
                      label="Wind direction"
                      value={mapping.windDirection ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], windDirection: value },
                        }))
                      }
                    />
                  )}
                  {isSolar ? (
                    <MappingSelect
                      label="Module temperature"
                      value={mapping.moduleTemperature ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], moduleTemperature: value },
                        }))
                      }
                    />
                  ) : (
                    <MappingSelect
                      label="Ambient temperature"
                      value={mapping.ambientTemperature ?? ""}
                      headers={headers}
                      onChange={(value) =>
                        setColumnMappings((previous) => ({
                          ...previous,
                          [file.name]: { ...previous[file.name], ambientTemperature: value },
                        }))
                      }
                    />
                  )}
                </div>

                <div className="mt-4">
                  <PowerChecklist
                    headers={headers}
                    selected={mapping.power ?? []}
                    collapsed={collapsedPowerLists[file.name] ?? false}
                    onToggleCollapsed={() =>
                      setCollapsedPowerLists((previous) => ({
                        ...previous,
                        [file.name]: !(previous[file.name] ?? false),
                      }))
                    }
                    onChange={(next) =>
                      setColumnMappings((previous) => ({
                        ...previous,
                        [file.name]: { ...previous[file.name], power: next },
                      }))
                    }
                  />
                </div>
              </div>
            );
          })}
        </WorkflowPanel>

        <WorkflowPanel
          step="Step 2"
          title="Site assumptions and reference weather"
          description="Confirm the plant context, timezone, reference-weather settings, and output horizon. Then save the setup and fetch the ERA reference weather."
          tone="emerald"
          highlighted={highlightedStep === 2}
          collapsed={collapsedSteps[2] ?? false}
          onToggle={() => toggleStep(2)}
          summary={referenceFetchResult ? `Reference weather ready from ${referenceFetchResult.dataset} for ${referenceFetchResult.dateRange.start} to ${referenceFetchResult.dateRange.end}.` : "Confirm the assumptions and fetch the reference weather."}
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div>
              <FieldLabel>Site type</FieldLabel>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white">
                {currentSite.site_type === "solar" ? "Solar PV" : "Wind"}
              </div>
            </div>
            <div>
              <FieldLabel>DC capacity</FieldLabel>
              <TextInput value={dcCapacity} onChange={(event) => setDcCapacity(event.currentTarget.value)} placeholder="kWp" />
            </div>
            <div>
              <FieldLabel>AC capacity</FieldLabel>
              <TextInput value={acCapacity} onChange={(event) => setAcCapacity(event.currentTarget.value)} placeholder="kW" />
            </div>
            <div>
              <FieldLabel>Latitude / Longitude (decimal degrees)</FieldLabel>
              <div className="grid grid-cols-2 gap-2">
                <TextInput value={latitude} onChange={(event) => setLatitude(event.currentTarget.value)} placeholder="Latitude" />
                <TextInput value={longitude} onChange={(event) => setLongitude(event.currentTarget.value)} placeholder="Longitude" />
              </div>
            </div>
            <div>
              <FieldLabel>Site timezone</FieldLabel>
              <SelectInput
                value={siteTimezone}
                onChange={(event) => {
                  setSiteTimezone(event.currentTarget.value);
                  setConfirmedTimezone("");
                }}
              >
                {SITE_TIMEZONE_OPTIONS.map((timezone) => (
                  <option key={timezone} value={timezone}>
                    {timezone}
                  </option>
                ))}
              </SelectInput>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleConfirmTimezone}
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] transition ${
                    isTimezoneConfirmed
                      ? "border-emerald-300/30 bg-emerald-400/15 text-emerald-100"
                      : "border-white/12 bg-white/6 text-slate-100 hover:border-white/20 hover:bg-white/10"
                  }`}
                >
                  {isTimezoneConfirmed ? "Timezone confirmed" : "Confirm timezone"}
                </button>
                <span className="text-xs text-slate-400">
                  REVEAL uses this timezone to align SCADA timestamps with ERA UTC data.
                </span>
              </div>
            </div>
          </div>

          {isSolar ? (
            <>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <FieldLabel>Tracker / mounting mode</FieldLabel>
                  <SelectInput value={trackerMode} onChange={(event) => setTrackerMode(event.currentTarget.value as TrackerMode)}>
                    <option value="fixed-tilt">Fixed tilt</option>
                    <option value="single-axis-tracker">Single-axis tracker</option>
                    <option value="dual-axis-tracker">Dual-axis tracker</option>
                  </SelectInput>
                </div>
                <div>
                  <FieldLabel>Module tilt</FieldLabel>
                  <TextInput value={moduleTiltDeg} onChange={(event) => setModuleTiltDeg(event.currentTarget.value)} placeholder="Degrees" />
                </div>
                <div>
                  <FieldLabel>Irradiance basis</FieldLabel>
                  <SelectInput value={irradianceBasis} onChange={(event) => setIrradianceBasis(event.currentTarget.value as IrradianceBasis)}>
                    <option value="poa">POA</option>
                    <option value="ghi">GHI</option>
                    <option value="tilted-reference">Tilted reference sensor</option>
                  </SelectInput>
                </div>
                <div>
                  <FieldLabel>Irradiance tilt</FieldLabel>
                  <TextInput value={irradianceTiltDeg} onChange={(event) => setIrradianceTiltDeg(event.currentTarget.value)} placeholder="Degrees" />
                </div>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div>
                  <FieldLabel>Specific yield basis</FieldLabel>
                  <SelectInput value={yieldScenario} onChange={(event) => setYieldScenario(event.currentTarget.value as YieldScenario)}>
                    <option value="measured">Use measured yield</option>
                    <option value="p50">Use custom P50 yield</option>
                    <option value="p75">Use custom P75 yield</option>
                    <option value="p90">Use custom P90 yield</option>
                  </SelectInput>
                </div>
                <div>
                  <FieldLabel>Specific yield input</FieldLabel>
                  <TextInput
                    value={measuredSpecificYieldDisplay}
                    onChange={(event) => setSpecificYieldInput(event.currentTarget.value)}
                    placeholder={yieldScenario === "measured" ? "Calculated after fit review" : "kWh/kWp"}
                    disabled={yieldScenario === "measured"}
                  />
                  {yieldScenario === "measured" && latestPreviewSummary?.measuredSpecificYieldKwhKwp != null ? (
                    <p className="mt-2 text-xs text-slate-400">
                      REVEAL measured yield: {latestPreviewSummary.measuredSpecificYieldKwhKwp.toLocaleString()} kWh/kWp
                    </p>
                  ) : null}
                </div>
                <div className="md:col-span-2 xl:col-span-2">
                  <FieldLabel>Guidance</FieldLabel>
                  <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] px-4 py-3 text-sm leading-6 text-slate-200/82">
                    {yieldBenchmark
                      ? `Rough location-based benchmark: ${yieldBenchmark.lower}-${yieldBenchmark.upper} kWh/kWp per year${trackerMode !== "fixed-tilt" ? " including tracker uplift" : ""}.`
                      : "Enter valid coordinates to display the rough location-based specific-yield benchmark."}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <FieldLabel>Hub height</FieldLabel>
                <TextInput defaultValue={String(site.hub_height_m ?? 120)} placeholder="m" />
              </div>
              <div>
                <FieldLabel>Rotor diameter</FieldLabel>
                <TextInput defaultValue={String(site.rotor_diameter_m ?? 136)} placeholder="m" />
              </div>
              <div>
                <FieldLabel>Expected AEP</FieldLabel>
                <TextInput defaultValue={String(site.expected_aep_gwh ?? "")} placeholder="GWh" />
              </div>
              <div>
                <FieldLabel>SCADA interval</FieldLabel>
                <TextInput defaultValue={String(site.interval_min)} placeholder="Minutes" />
              </div>
            </div>
          )}
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div>
              <FieldLabel>Satellite / reanalysis source</FieldLabel>
              <SelectInput value={satelliteSource} onChange={(event) => setSatelliteSource(event.currentTarget.value as SatelliteSource)}>
                <option value="era5-land">ERA5-Land</option>
                <option value="era5">ERA5</option>
                <option value="nasa-power">NASA POWER</option>
                <option value="merra-2">MERRA-2</option>
              </SelectInput>
            </div>
            <div>
              <FieldLabel>Additional projection horizon (years)</FieldLabel>
              <TextInput value={correlationYears} onChange={(event) => setCorrelationYears(event.currentTarget.value)} placeholder="Years" />
            </div>
            <div>
              <FieldLabel>Actual data start</FieldLabel>
              <TextInput value={actualDataStartDate} onChange={(event) => setActualDataStartDate(event.currentTarget.value)} placeholder="dd/mm/yyyy" />
            </div>
            <div>
              <FieldLabel>Actual data end</FieldLabel>
              <TextInput value={actualDataEndDate} onChange={(event) => setActualDataEndDate(event.currentTarget.value)} placeholder="dd/mm/yyyy" />
            </div>
            <div>
              <FieldLabel>Output time step</FieldLabel>
              <SelectInput value={outputResolution} onChange={(event) => setOutputResolution(event.currentTarget.value as OutputResolution)}>
                <option value="10min">10-minute</option>
                <option value="30min">30-minute</option>
                <option value="hourly">Hourly</option>
              </SelectInput>
            </div>
            <div>
              <FieldLabel>Output file format</FieldLabel>
              <SelectInput value={outputFormat} onChange={(event) => setOutputFormat(event.currentTarget.value as OutputFormat)}>
                <option value="csv">CSV</option>
                <option value="xlsx">Excel (.xlsx)</option>
              </SelectInput>
            </div>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="rounded-[24px] border border-white/10 bg-white/5 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/55">Selected workflow</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                  <p className="text-xs text-slate-400">Reference data</p>
                  <p className="mt-2 text-lg font-semibold text-white">
                    {satelliteSource === "era5-land" ? "ERA5-Land" : satelliteSource === "nasa-power" ? "NASA POWER" : satelliteSource === "merra-2" ? "MERRA-2" : "ERA5"}
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                  <p className="text-xs text-slate-400">Target output</p>
                  <p className="mt-2 text-lg font-semibold text-white">
                    {outputResolution === "10min" ? "10-minute" : outputResolution === "30min" ? "30-minute" : "Hourly"} · {outputFormat.toUpperCase()}
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-[24px] border border-orange-DEFAULT/20 bg-orange-DEFAULT/8 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-orange-100/80">Planned output</p>
              <p className="mt-3 text-sm leading-7 text-slate-100/88">
                REVEAL will calibrate the measured site file against the chosen long-term weather source, review the cleaned irradiation fit and specific yield, then generate a modelling-ready production file over the selected horizon.
              </p>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button variant="ghost" size="lg" className="rounded-2xl border border-sky-200/20 bg-sky-300/15 text-white hover:bg-sky-300/22" onClick={handleSaveSetup}>
              2A. Save setup
            </Button>
            <Button
              variant="ghost"
              size="lg"
              className="rounded-2xl border border-emerald-200/20 bg-emerald-300/15 text-white hover:bg-emerald-300/22"
              onClick={handleFetchReferenceWeather}
              loading={fetchingReference}
            >
              2B. Fetch reference weather
            </Button>
          </div>

          {setupSaved ? (
            <div className="mt-4 rounded-2xl border border-emerald-300/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              Modelling setup saved locally for this site.
            </div>
          ) : null}
          {referenceMessage ? (
            <div className="mt-4 rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] px-4 py-3 text-sm text-slate-100">
              {referenceMessage}
            </div>
          ) : null}
          {fetchingReference ? (
            <div className="mt-4 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Reference weather progress</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">Downloading ERA reference weather</p>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                  {referenceFetchProgress}%
                </div>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(88,176,255,0.96),rgba(165,214,255,0.96))] transition-all duration-700"
                  style={{ width: `${referenceFetchProgress}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-slate-300/84">
                REVEAL is contacting the selected reanalysis source, requesting the point time-series, and caching the result for the long-term run.
              </p>
            </div>
          ) : null}
          {referenceFetchResult ? (
            <div className="mt-4 space-y-4">
              {showRunNextPrompt ? (
                <div className="rounded-[24px] border border-emerald-300/30 bg-emerald-500/10 p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100/75">Next step</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                    Reference weather is ready. Screen the measured data before analysing the fit and yield.
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-200/82">
                    REVEAL has the weather reference and cached file. The next action is to remove obvious flatlined power periods from the measured dataset, then calculate the irradiation-fit checks, regression, and specific-yield review.
                  </p>
                </div>
              ) : null}
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Reference fetch summary</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-100">
                    <p><span className="text-slate-400">Dataset:</span> {referenceFetchResult.dataset}</p>
                    <p><span className="text-slate-400">Source:</span> {referenceFetchResult.source}</p>
                    <p><span className="text-slate-400">Rows:</span> {referenceFetchResult.rowCount.toLocaleString()}</p>
                    <p><span className="text-slate-400">Cache:</span> {referenceFetchResult.cached ? "Loaded from cache" : "Freshly downloaded"}</p>
                    <p><span className="text-slate-400">File:</span> {referenceFetchResult.fileName}</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Location and variables</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-100">
                    <p><span className="text-slate-400">Requested:</span> {referenceFetchResult.locationRequested.latitude}, {referenceFetchResult.locationRequested.longitude}</p>
                    <p><span className="text-slate-400">Used:</span> {referenceFetchResult.locationUsed.latitude}, {referenceFetchResult.locationUsed.longitude}</p>
                    <p><span className="text-slate-400">Period:</span> {referenceFetchResult.dateRange.start} to {referenceFetchResult.dateRange.end}</p>
                    <p><span className="text-slate-400">Variables:</span> {referenceFetchResult.variables.join(", ")}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </WorkflowPanel>
        <WorkflowPanel
          step="Step 3"
          title="Screen bad data"
          description="Remove clearly frozen power and weather periods before REVEAL builds the fit review. This keeps the later calibration focused on cleaner measured data."
          tone="amber"
          highlighted={highlightedStep === 3}
          collapsed={collapsedSteps[3] ?? false}
          onToggle={() => toggleStep(3)}
          summary={
            visibleScreeningSummary
              ? `${visibleScreeningSummary.badDataEvents?.toLocaleString() ?? "0"} flagged event${visibleScreeningSummary.badDataEvents === 1 ? "" : "s"} across ${visibleScreeningSummary.badDataRows?.toLocaleString() ?? "0"} excluded rows.`
              : "Run the bad-data screen once the reference weather is ready."
          }
        >
          <div className="flex flex-wrap gap-3">
            <Button
              variant="ghost"
              size="lg"
              className="rounded-2xl border border-amber-200/20 bg-amber-300/15 text-white hover:bg-amber-300/22"
              onClick={handleScreenBadData}
              loading={startingLongTermJob && startingRunMode === "screening"}
              disabled={!Boolean(referenceFetchResult) || fetchingReference || !isTimezoneConfirmed}
              title={!referenceFetchResult ? "Fetch reference weather first" : !isTimezoneConfirmed ? "Confirm the site timezone first" : undefined}
            >
              3. Screen bad data
            </Button>
          </div>

          {runMessage && longTermJob?.runMode === "screening" ? (
            <div className="mt-4 rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] px-4 py-3 text-sm text-slate-100">
              {runMessage}
            </div>
          ) : null}
          {longTermJob && longTermJob.runMode === "screening" ? (
            <div className="mt-4 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Bad-data screening progress</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.stage ?? (longTermJob.status === "complete" ? "Complete" : "In progress")}
                  </p>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                  {longTermJob.progress}%
                </div>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(243,146,0,0.96),rgba(255,210,136,0.96))] transition-all duration-700"
                  style={{ width: `${longTermJob.progress}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-slate-300/84">
                {longTermJob.status === "error"
                  ? longTermJob.error
                  : longTermJob.status === "complete"
                    ? "Bad-data screening is ready. Review the flagged periods before moving to the fit-and-yield step."
                    : "REVEAL is checking the measured power and irradiance channels for repeated-value periods and compiling the screening summary."}
              </p>
            </div>
          ) : null}
          {visibleScreeningSummary ? (
            <div className="mt-4 rounded-[24px] border border-amber-300/20 bg-amber-500/8 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/75">Bad-data screening</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                    {visibleScreeningSummary.badDataApplied
                      ? "Flagged repeated-value periods were excluded before the fit review."
                      : "No obvious repeated-value periods were found by the screening rule."}
                  </p>
                  <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-200/82">{visibleScreeningSummary.badDataRule}</p>
                </div>
                <div className="grid min-w-[16rem] gap-2 rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm text-slate-100">
                  <p><span className="text-slate-400">Measured rows:</span> {visibleScreeningSummary.totalMeasuredRows?.toLocaleString() ?? "0"}</p>
                  <p><span className="text-slate-400">Excluded rows:</span> {visibleScreeningSummary.badDataRows?.toLocaleString() ?? "0"}</p>
                  <p><span className="text-slate-400">Excluded hours:</span> {visibleScreeningSummary.badDataHours?.toLocaleString() ?? "0"}</p>
                  <p><span className="text-slate-400">Flagged events:</span> {visibleScreeningSummary.badDataEvents?.toLocaleString() ?? "0"}</p>
                  <p><span className="text-slate-400">Power rows flagged:</span> {visibleScreeningSummary.badPowerRows?.toLocaleString() ?? "0"}</p>
                  <p><span className="text-slate-400">Weather rows flagged:</span> {visibleScreeningSummary.badWeatherRows?.toLocaleString() ?? "0"}</p>
                </div>
              </div>
              {screeningHeatmapMonths.length ? (
                <div className="mt-5 rounded-[24px] border border-white/10 bg-[rgba(4,18,28,0.5)] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/75">Bad-data heat map</p>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-200/82">
                        Each tile represents one local day. REVEAL marks a day when a flagged frozen power or irradiance window touches that date, so you can spot excluded blocks such as the late-October period immediately.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-200/84">
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Good data</span>
                      <span className="rounded-full border border-sky-300/30 bg-sky-400/18 px-3 py-1 text-sky-100">Power flagged</span>
                      <span className="rounded-full border border-orange-300/30 bg-orange-400/18 px-3 py-1 text-orange-100">Irradiance flagged</span>
                      <span className="rounded-full border border-rose-300/30 bg-rose-400/18 px-3 py-1 text-rose-100">Both flagged</span>
                    </div>
                  </div>
                  <div className="mt-4 space-y-3">
                    {screeningHeatmapMonths.map((month) => (
                      <div key={month.key} className="grid gap-2 rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.03)] px-3 py-2 lg:grid-cols-[8rem_1fr] lg:items-center">
                        <div className="text-sm font-semibold text-white">{month.label}</div>
                        <div className="grid grid-cols-[repeat(31,minmax(0,1fr))] gap-1">
                          {month.cells.map((cell) => {
                            const tone =
                              cell.status === "both"
                                ? "border-red-400 bg-[linear-gradient(135deg,rgba(56,189,248,0.96)_0%,rgba(56,189,248,0.96)_48%,rgba(251,146,60,0.96)_52%,rgba(251,146,60,0.96)_100%)] text-white"
                                : cell.status === "power"
                                  ? "border-red-400 bg-sky-400 text-white"
                                  : cell.status === "weather"
                                    ? "border-red-400 bg-orange-400 text-white"
                                    : "border-white/10 bg-white/7 text-slate-200";
                            return (
                              <div
                                key={cell.key}
                                title={`${cell.label} · ${
                                  cell.status === "both"
                                    ? "Power and irradiance flagged"
                                    : cell.status === "power"
                                      ? "Power flagged"
                                      : cell.status === "weather"
                                        ? "Irradiance flagged"
                                        : "Good data"
                                }`}
                                className={`flex h-5 items-center justify-center rounded-[4px] border text-[9px] font-semibold ${tone}`}
                              >
                                {cell.day}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </WorkflowPanel>

        <WorkflowPanel
          step="Step 4"
          title="Review fit and yield"
          description="Analyse the cleaned irradiation fit, regression line, seasonality, and measured specific yield before the projection step unlocks."
          tone="teal"
          highlighted={highlightedStep === 4}
          collapsed={collapsedSteps[4] ?? false}
          onToggle={() => toggleStep(4)}
          summary={
            hasCurrentPreview
              ? `Fit review ready with R² ${latestPreviewSummary?.irradianceFitR2 ?? "N/A"} across ${latestPreviewSummary?.irradianceFitPoints ?? "0"} matched days.`
              : "Run the fit-and-yield review after screening the bad data."
          }
        >
          <div className="flex flex-wrap gap-3">
            <Button
              variant="ghost"
              size="lg"
              className="rounded-2xl border border-teal-200/20 bg-teal-300/15 text-white hover:bg-teal-300/22"
              onClick={handleAnalyseFitAndYield}
              loading={startingLongTermJob && startingRunMode === "preview"}
              disabled={!Boolean(referenceFetchResult) || fetchingReference || !isTimezoneConfirmed || !hasCurrentScreening}
              title={
                !referenceFetchResult
                  ? "Fetch reference weather first"
                  : !isTimezoneConfirmed
                    ? "Confirm the site timezone first"
                    : !hasCurrentScreening
                      ? "Run the bad-data screen first"
                      : undefined
              }
            >
              4. Analyse fit and yield
            </Button>
          </div>

          {runMessage && longTermJob?.runMode === "preview" ? (
            <div className="mt-4 rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] px-4 py-3 text-sm text-slate-100">
              {runMessage}
            </div>
          ) : null}
          {longTermJob && longTermJob.runMode === "preview" ? (
            <div className="mt-4 rounded-[24px] border border-white/12 bg-[rgba(5,20,32,0.9)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Fit and yield progress</p>
                  <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.stage ?? (longTermJob.status === "complete" ? "Complete" : "In progress")}
                  </p>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100">
                  {longTermJob.progress}%
                </div>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(243,146,0,0.96),rgba(255,210,136,0.96))] transition-all duration-700"
                  style={{ width: `${longTermJob.progress}%` }}
                />
              </div>
              <p className="mt-3 text-sm text-slate-300/84">
                {longTermJob.status === "error"
                  ? longTermJob.error
                  : longTermJob.status === "complete"
                    ? "Fit-and-yield review is ready. Check the charts and specific yield before continuing."
                    : "REVEAL is analysing the cleaned comparison period, checking the irradiation fit, and calculating the specific-yield review."}
              </p>
            </div>
          ) : null}

          {longTermJob?.status === "complete" ? (
            <div className="mt-5 space-y-4">
              {visibleScreeningSummary ? (
                <div className="rounded-[24px] border border-amber-300/20 bg-amber-500/8 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/75">Bad-data screening</p>
                      <p className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">
                        {visibleScreeningSummary.badDataApplied
                          ? "Flatlined measured power periods were excluded before the long-term analysis."
                          : "No obvious flatlined measured power periods were found by the screening rule."}
                      </p>
                      <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-200/82">
                        {visibleScreeningSummary.badDataRule}
                      </p>
                    </div>
                    <div className="grid min-w-[16rem] gap-2 rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm text-slate-100">
                      <p><span className="text-slate-400">Measured rows:</span> {visibleScreeningSummary.totalMeasuredRows?.toLocaleString() ?? "0"}</p>
                      <p><span className="text-slate-400">Excluded rows:</span> {visibleScreeningSummary.badDataRows?.toLocaleString() ?? "0"}</p>
                      <p><span className="text-slate-400">Excluded hours:</span> {visibleScreeningSummary.badDataHours?.toLocaleString() ?? "0"}</p>
                      <p><span className="text-slate-400">Flagged events:</span> {visibleScreeningSummary.badDataEvents?.toLocaleString() ?? "0"}</p>
                      <p><span className="text-slate-400">Power rows flagged:</span> {visibleScreeningSummary.badPowerRows?.toLocaleString() ?? "0"}</p>
                      <p><span className="text-slate-400">Weather rows flagged:</span> {visibleScreeningSummary.badWeatherRows?.toLocaleString() ?? "0"}</p>
                    </div>
                  </div>
                  {visibleScreeningSummary.badPowerWindows?.length ? (
                    <div className="mt-4">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/70">Flagged power windows</p>
                      <div className="grid gap-3 lg:grid-cols-2">
                        {visibleScreeningSummary.badPowerWindows.map((window, index) => (
                          <div key={`${window.start}-${index}`} className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm text-slate-100">
                            <p><span className="text-slate-400">Start:</span> {window.start}</p>
                            <p><span className="text-slate-400">End:</span> {window.end}</p>
                            <p><span className="text-slate-400">Duration:</span> {window.durationHours} h</p>
                            <p><span className="text-slate-400">Rows:</span> {window.rowCount.toLocaleString()}</p>
                            <p><span className="text-slate-400">Stuck power:</span> {window.stuckPowerKw != null ? `${window.stuckPowerKw.toLocaleString()} kW` : "N/A"}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {visibleScreeningSummary.badWeatherWindows?.length ? (
                    <div className="mt-4">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/70">Flagged weather windows</p>
                      <div className="grid gap-3 lg:grid-cols-2">
                        {visibleScreeningSummary.badWeatherWindows.map((window, index) => (
                          <div key={`${window.start}-${index}`} className="rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm text-slate-100">
                            <p><span className="text-slate-400">Start:</span> {window.start}</p>
                            <p><span className="text-slate-400">End:</span> {window.end}</p>
                            <p><span className="text-slate-400">Duration:</span> {window.durationHours} h</p>
                            <p><span className="text-slate-400">Rows:</span> {window.rowCount.toLocaleString()}</p>
                            <p><span className="text-slate-400">Stuck irradiance:</span> {window.stuckIrradiance != null ? `${window.stuckIrradiance.toLocaleString()} W/m²` : "N/A"}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">
                    {longTermJob.runMode === "screening" ? "Bad-data screening summary" : longTermJob.runMode === "preview" ? "Fit and yield review summary" : "Run summary"}
                  </p>
                  <div className="mt-3 space-y-2 text-sm text-slate-100">
                    <p><span className="text-slate-400">Measured period:</span> {longTermJob.summary?.measuredStart} to {longTermJob.summary?.measuredEnd}</p>
                    <p><span className="text-slate-400">Measured coverage:</span> {longTermJob.summary?.measuredDurationYears} years</p>
                    <p><span className="text-slate-400">Full measured years used:</span> {longTermJob.summary?.fullMeasuredYears ?? 0}</p>
                    <p><span className="text-slate-400">Measured raw energy used:</span> {longTermJob.summary?.measuredTotalEnergyMwh?.toLocaleString()} MWh</p>
                    <p><span className="text-slate-400">Site timezone:</span> {longTermJob.summary?.siteTimezone}</p>
                    <p><span className="text-slate-400">Additional projection horizon:</span> {longTermJob.summary?.correlationYears} years</p>
                    <p><span className="text-slate-400">Projection starts:</span> {longTermJob.summary?.projectionStart}</p>
                    <p><span className="text-slate-400">Power channels:</span> {longTermJob.summary?.selectedPowerChannels}</p>
                    <p><span className="text-slate-400">Bad-data events:</span> {longTermJob.summary?.badDataEvents ?? 0}</p>
                    <p><span className="text-slate-400">Bad-data rows excluded:</span> {longTermJob.summary?.badDataRows?.toLocaleString() ?? "0"}</p>
                    <p><span className="text-slate-400">Bad-data hours excluded:</span> {longTermJob.summary?.badDataHours?.toLocaleString() ?? "0"} h</p>
                    {Array.isArray(longTermJob.summary?.selectedPowerColumnNames) && longTermJob.summary.selectedPowerColumnNames.length ? (
                      <p><span className="text-slate-400">Power column set:</span> {longTermJob.summary.selectedPowerColumnNames.join(", ")}</p>
                    ) : null}
                    <p><span className="text-slate-400">Reference source:</span> {longTermJob.summary?.referenceDataset}</p>
                    <p><span className="text-slate-400">Reference irradiance mode:</span> {longTermJob.summary?.referenceIrradianceMode}</p>
                    {longTermJob.summary?.note ? <p><span className="text-slate-400">Note:</span> {longTermJob.summary.note}</p> : null}
                  </div>
                </div>
                {longTermJob.runMode === "projection" ? (
                  <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Output file</p>
                    <div className="mt-3 space-y-3 text-sm text-slate-100">
                      <p><span className="text-slate-400">File:</span> {longTermJob.fileName}</p>
                      <p><span className="text-slate-400">Format:</span> {longTermJob.outputFormat.toUpperCase()}</p>
                      {longTermJob.downloadUrl ? (
                        <a
                          href={longTermJob.downloadUrl}
                          className="inline-flex rounded-2xl bg-orange-DEFAULT px-4 py-3 font-semibold text-white transition hover:bg-orange-accent"
                        >
                          Download hourly production file
                        </a>
                      ) : null}
                    </div>
                  </div>
                ) : longTermJob.runMode === "screening" ? (
                  <div className="rounded-2xl border border-amber-300/20 bg-amber-500/10 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-100/75">Next step</p>
                    <div className="mt-3 space-y-3 text-sm text-amber-50">
                      <p>REVEAL has screened the measured power channels and excluded the flagged repeated-value periods from the later long-term steps.</p>
                      <p>Continue with the fit-and-yield review so you can see the cleaned irradiance correlation and measured specific yield.</p>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/10 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100/75">Decision gate</p>
                    <div className="mt-3 space-y-3 text-sm text-emerald-50">
                      <p>Review the measured specific yield, projected AEP, and irradiance-fit R² before generating the output file.</p>
                      <p>If the assumptions look wrong, adjust the inputs or upload better data, then rerun the fit-and-yield review.</p>
                    </div>
                  </div>
                )}
              </div>

              {limitedFullYearsWarning ? (
                <div className="rounded-2xl border border-amber-300/30 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100">
                  Attention: REVEAL found only {longTermJob.summary?.fullMeasuredYears} full measured year{longTermJob.summary?.fullMeasuredYears === 1 ? "" : "s"} for
                  the benchmarking step. It is better to supply at least 3 full years of actual data to ensure stronger correlation and more reliable extrapolation.
                </div>
              ) : null}

              <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Measured AEP</p>
                  <p className="mt-3 font-dolfines text-2xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.summary?.measuredAnnualizedAepMwh?.toLocaleString()} MWh/yr
                  </p>
                  <p className="mt-2 text-sm text-slate-300/80">Annualized from the available measured period, pro-rata where required.</p>
                </div>
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Projected AEP</p>
                  <p className="mt-3 font-dolfines text-2xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.summary?.projectedAverageAepMwh?.toLocaleString()} MWh/yr
                  </p>
                  <p className="mt-2 text-sm text-slate-300/80">Average annual energy across the projected period.</p>
                </div>
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Measured specific yield</p>
                  <p className="mt-3 font-dolfines text-2xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.summary?.measuredSpecificYieldKwhKwp != null ? `${longTermJob.summary.measuredSpecificYieldKwhKwp.toLocaleString()} kWh/kWp` : "N/A"}
                  </p>
                  <p className="mt-2 text-sm text-slate-300/80">Derived from annualized measured AEP and configured DC capacity.</p>
                </div>
                <div className="rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Projected specific yield</p>
                  <p className="mt-3 font-dolfines text-2xl font-semibold tracking-[0.04em] text-white">
                    {longTermJob.summary?.projectedSpecificYieldKwhKwp != null ? `${longTermJob.summary.projectedSpecificYieldKwhKwp.toLocaleString()} kWh/kWp` : "N/A"}
                  </p>
                  <p className="mt-2 text-sm text-slate-300/80">
                    {longTermJob.summary?.yieldScenario && longTermJob.summary.yieldScenario !== "measured"
                      ? `Projected using the user-supplied ${longTermJob.summary.yieldScenario.toUpperCase()} yield input.`
                      : "Projected from the measured calibrated yield response."}
                  </p>
                </div>
              </div>

              {lowSpecificYieldWarning && yieldBenchmark ? (
                <div className="rounded-2xl border border-amber-300/30 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100">
                  Measured specific yield appears low for this location. REVEAL&apos;s rough benchmark for these coordinates is about {yieldBenchmark.lower}-
                  {yieldBenchmark.upper} kWh/kWp per year{trackerMode !== "fixed-tilt" ? " with tracker uplift" : ""}, while the measured annualized
                  result is {longTermJob.summary?.measuredSpecificYieldKwhKwp} kWh/kWp. Please confirm whether this reflects genuine operational losses,
                  curtailed operation, incomplete data coverage, or whether you want to override the projection using your own P50/P75/P90 yield.
                </div>
              ) : null}

              <div className="rounded-[24px] border border-white/12 bg-[rgba(255,255,255,0.05)] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-dolfines text-xl font-semibold tracking-[0.04em] text-white">Irradiation fit check</p>
                    <p className="mt-2 text-sm text-slate-300/82">
                      Site irradiation versus reference irradiation during the measured comparison period. Use this as the confidence check for the long-term extrapolation.
                    </p>
                    <p className="mt-3 max-w-4xl rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.04)] px-4 py-3 text-xs leading-6 text-slate-300/84">
                      Fit methodology: REVEAL only compares matched periods where valid site irradiance exists. A matched day means at least 6 aligned hourly periods
                      with valid values on the same day in both the site and ERA datasets. If site irradiance is missing for part of a day, the corresponding ERA hours
                      are excluded as well, so the regression is built from like-for-like irradiation totals rather than full-day ERA values against partial measured
                      coverage.
                    </p>
                    <p className="mt-3 text-xs leading-6 text-slate-400/90">
                      The plotted point count represents valid matched days, not raw 10-minute SCADA rows. Low-irradiation days are now kept in the regression as long as
                      the day still has at least 6 valid matched hours.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.9)] px-4 py-3 text-sm text-slate-100">
                    <p><span className="text-slate-400">R²:</span> {longTermJob.summary?.irradianceFitR2}</p>
                    <p><span className="text-slate-400">Slope:</span> {longTermJob.summary?.irradianceFitSlope}</p>
                    <p><span className="text-slate-400">Points:</span> {longTermJob.summary?.irradianceFitPoints}</p>
                    <p><span className="text-slate-400">Aggregation:</span> {longTermJob.summary?.irradianceFitAggregation ?? "overlap points"}</p>
                    <p><span className="text-slate-400">Total days:</span> {longTermJob.summary?.irradianceFitTotalDays ?? "N/A"}</p>
                    <p><span className="text-slate-400">Matched days:</span> {longTermJob.summary?.irradianceFitMatchedDays ?? "N/A"}</p>
                    <p><span className="text-slate-400">Excluded days:</span> {longTermJob.summary?.irradianceFitExcludedDays ?? "N/A"}</p>
                  </div>
                </div>
                <div className="mt-5 h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 28, left: 62, bottom: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" />
                      <XAxis
                        type="number"
                        dataKey="reference_irradiance_kwh_m2"
                        name="Reference daily irradiation"
                        label={{ value: "Reference irradiation (kWh/m²/day)", position: "insideBottom", offset: -10, fill: "#9fb4c8", fontSize: 11 }}
                        stroke="#9fb4c8"
                        tick={{ fill: "#9fb4c8", fontSize: 12 }}
                      />
                      <YAxis
                        type="number"
                        dataKey="site_irradiance_kwh_m2"
                        name="Site daily irradiation"
                        label={{ value: "Site irradiation (kWh/m²/day)", angle: -90, position: "insideLeft", dx: -24, dy: 132, fill: "#9fb4c8", fontSize: 11 }}
                        stroke="#9fb4c8"
                        tick={{ fill: "#9fb4c8", fontSize: 12 }}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        contentStyle={{ background: "rgba(3,16,26,0.96)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16 }}
                        labelStyle={{ color: "#fff" }}
                        itemStyle={{ color: "#fff" }}
                        wrapperStyle={{ color: "#fff" }}
                      />
                      {fitLineSegment ? (
                        <ReferenceLine
                          segment={fitLineSegment}
                          stroke="#f39200"
                          strokeWidth={2}
                          strokeDasharray="7 5"
                        />
                      ) : null}
                      <Scatter data={longTermJob.charts?.irradianceFit ?? []} fill="#58b0ff" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-[24px] border border-white/8 bg-[rgba(255,255,255,0.04)] p-5">
                  <p className="font-dolfines text-xl font-semibold tracking-[0.04em] text-white">Annual production overview</p>
                  <p className="mt-2 text-sm text-slate-300/82">Annual energy production in MWh with annual reference irradiation shown on a secondary axis. This helps distinguish whether a strong measured year comes from stronger resource, stronger operating yield, or both. Partial measured years such as 2024 are shown for context in the chart, but they are still excluded from the benchmark metrics and the future projection calibration.</p>
                  <div className="mt-5 h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={annualChartData} margin={{ top: 10, right: 54, left: 46, bottom: 32 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" />
                        <XAxis dataKey="label" stroke="#9fb4c8" tick={{ fill: "#9fb4c8", fontSize: 12 }} />
                        <YAxis
                          yAxisId="energy"
                          stroke="#9fb4c8"
                          tick={{ fill: "#9fb4c8", fontSize: 12 }}
                          label={{ value: "Energy (MWh/year)", angle: -90, position: "insideLeft", dx: -22, dy: 132, fill: "#9fb4c8", fontSize: 11 }}
                        />
                        <YAxis
                          yAxisId="irradiation"
                          orientation="right"
                          stroke="#cbd5e1"
                          tick={{ fill: "#cbd5e1", fontSize: 12 }}
                          label={{ value: "Reference irradiation (kWh/m²/year)", angle: 90, position: "insideRight", dx: 24, dy: 132, fill: "#cbd5e1", fontSize: 11 }}
                        />
                        <Tooltip
                          cursor={{ fill: "rgba(148,163,184,0.08)" }}
                          contentStyle={{ background: "rgba(3,16,26,0.96)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16 }}
                          labelStyle={{ color: "#fff" }}
                        />
                        <Legend />
                        <Bar yAxisId="energy" dataKey="actual" name="Measured" fill="#f39200" radius={[8, 8, 0, 0]} />
                        <Bar yAxisId="energy" dataKey="projected" name="Projected" fill="#58b0ff" radius={[8, 8, 0, 0]} />
                        <Line yAxisId="irradiation" type="monotone" dataKey="referenceIrradiation" name="Reference irradiation" stroke="#cbd5e1" strokeWidth={2.5} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="rounded-[24px] border border-white/12 bg-[rgba(255,255,255,0.05)] p-5">
                  <p className="font-dolfines text-xl font-semibold tracking-[0.04em] text-white">Seasonality</p>
                  <p className="mt-2 text-sm text-slate-300/82">Average monthly energy production per year in MWh, with average monthly reference irradiation shown as bars on a secondary axis. This compares the projected seasonal shape against the measured operating profile on a like-for-like basis. For Pruny, the October peak is coming from the measured 2023 data rather than being introduced by the projection.</p>
                  <div className="mt-5 h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={monthlyChartData} margin={{ top: 10, right: 54, left: 46, bottom: 24 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" />
                        <XAxis dataKey="label" stroke="#9fb4c8" tick={{ fill: "#9fb4c8", fontSize: 12 }} />
                        <YAxis
                          yAxisId="energy"
                          stroke="#9fb4c8"
                          tick={{ fill: "#9fb4c8", fontSize: 12 }}
                          label={{ value: "Energy (MWh/month)", angle: -90, position: "insideLeft", dx: -22, dy: 132, fill: "#9fb4c8", fontSize: 11 }}
                        />
                        <YAxis
                          yAxisId="irradiation"
                          orientation="right"
                          stroke="#cbd5e1"
                          tick={{ fill: "#cbd5e1", fontSize: 12 }}
                          label={{ value: "Reference irradiation (kWh/m²/month)", angle: 90, position: "insideRight", dx: 24, dy: 132, fill: "#cbd5e1", fontSize: 11 }}
                        />
                        <Tooltip
                          contentStyle={{ background: "rgba(3,16,26,0.96)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16 }}
                          labelStyle={{ color: "#fff" }}
                        />
                        <Legend />
                        <Bar yAxisId="irradiation" dataKey="referenceIrradiation" name="Reference irradiation" fill="rgba(203,213,225,0.28)" radius={[6, 6, 0, 0]} />
                        <Line yAxisId="energy" type="monotone" dataKey="actual" name="Measured" stroke="#f39200" strokeWidth={3} dot={false} />
                        <Line yAxisId="energy" type="monotone" dataKey="projected" name="Projected" stroke="#58b0ff" strokeWidth={3} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </WorkflowPanel>

        <WorkflowPanel
          step="Step 5"
          title="Confirm yield and download the data"
          description="Lock in the specific-yield basis, generate the long-term output file, and download the modelling-ready production data when the review looks sound."
          tone="violet"
          highlighted={highlightedStep === 5}
          collapsed={collapsedSteps[5] ?? false}
          onToggle={() => toggleStep(5)}
          summary={
            longTermJob?.runMode === "projection" && longTermJob.status === "complete"
              ? `${longTermJob.fileName ?? "Long-term output"} is ready to download.`
              : isSpecificYieldConfirmed
                ? "Specific yield confirmed. Generate the output file when you are ready."
                : "Confirm the specific yield basis after reviewing the fit and yield."
          }
        >
          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[24px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-100/80">Specific yield basis</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <FieldLabel>Specific yield basis</FieldLabel>
                  <SelectInput value={yieldScenario} onChange={(event) => setYieldScenario(event.currentTarget.value as YieldScenario)}>
                    <option value="measured">Use measured yield</option>
                    <option value="p50">Use custom P50 yield</option>
                    <option value="p75">Use custom P75 yield</option>
                    <option value="p90">Use custom P90 yield</option>
                  </SelectInput>
                </div>
                <div>
                  <FieldLabel>Specific yield input</FieldLabel>
                  <TextInput
                    value={measuredSpecificYieldDisplay}
                    onChange={(event) => setSpecificYieldInput(event.currentTarget.value)}
                    placeholder={yieldScenario === "measured" ? "Calculated after fit review" : "kWh/kWp"}
                    disabled={yieldScenario === "measured"}
                  />
                </div>
              </div>
              {yieldScenario === "measured" && latestPreviewSummary?.measuredSpecificYieldKwhKwp != null ? (
                <p className="mt-3 text-sm text-slate-300/84">
                  REVEAL measured yield from the reviewed dataset: {latestPreviewSummary.measuredSpecificYieldKwhKwp.toLocaleString()} kWh/kWp.
                </p>
              ) : null}
            </div>
            <div className="rounded-[24px] border border-violet-300/20 bg-violet-500/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-100/80">Action flow</p>
              <p className="mt-3 text-sm leading-7 text-violet-50/88">
                Confirm the yield basis only once the Step 4 review looks representative. The final projection uses the reviewed assumptions plus the cleaned measured dataset.
              </p>
              <div className="mt-4 grid gap-3">
                <Button
                  variant="ghost"
                  size="lg"
                  className="w-full rounded-2xl border border-violet-200/20 bg-violet-300/15 text-white hover:bg-violet-300/22"
                  onClick={handleConfirmSpecificYield}
                  disabled={!canConfirmSpecificYield || !hasCurrentPreview}
                  title={!canConfirmSpecificYield ? "Fetch reference weather and upload measured data first" : !hasCurrentPreview ? "Run the fit-and-yield review first" : undefined}
                >
                  {isSpecificYieldConfirmed ? "5A. Specific yield confirmed" : "5A. Confirm specific yield"}
                </Button>
                <Button
                  variant="ghost"
                  size="lg"
                  className="w-full rounded-2xl border border-violet-200/20 bg-violet-300/15 text-white hover:bg-violet-300/22"
                  onClick={handleRunLongTermCorrelation}
                  loading={startingLongTermJob && startingRunMode === "projection"}
                  disabled={!canRunLongTermCorrelation}
                  title={!canRunLongTermCorrelation ? "Analyse and confirm the fit-and-yield step first" : undefined}
                >
                  5B. Generate output file
                </Button>
                <button
                  type="button"
                  disabled
                  className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-slate-500 cursor-not-allowed"
                  title="Coming soon"
                >
                  Optimize to P50
                </button>
              </div>
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-300/76">
            {canRunLongTermCorrelation
              ? "This run generates the first operational extrapolation. P50 optimization stays disabled until the normalization layer is added."
              : !referenceFetchResult
                ? "Fetch reference weather first, then screen the bad data and review the fit and yield."
                : !isTimezoneConfirmed
                  ? "Confirm the site timezone before REVEAL can align the SCADA data with ERA UTC timestamps."
                  : !hasCurrentScreening
                    ? "Run the bad-data screen first so REVEAL can remove flatlined measured periods before the fit review."
                    : !hasCurrentPreview
                      ? "Run the fit-and-yield review first so REVEAL can show the charts, regression, and correlation checks."
                      : !isSpecificYieldConfirmed
                        ? "Confirm the specific yield basis after reviewing the fit-and-yield results."
                        : "Generate the long-term output file when you are ready."}
          </p>
          {longTermJob?.runMode === "projection" && longTermJob.status === "complete" ? (
            <div className="mt-4 rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.05)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Download the data</p>
              <div className="mt-3 space-y-3 text-sm text-slate-100">
                <p><span className="text-slate-400">File:</span> {longTermJob.fileName}</p>
                <p><span className="text-slate-400">Format:</span> {longTermJob.outputFormat.toUpperCase()}</p>
                {longTermJob.downloadUrl ? (
                  <a
                    href={longTermJob.downloadUrl}
                    className="inline-flex rounded-2xl bg-orange-DEFAULT px-4 py-3 font-semibold text-white transition hover:bg-orange-accent"
                  >
                    Download the data
                  </a>
                ) : null}
              </div>
            </div>
          ) : null}
        </WorkflowPanel>
      </div>
    </div>
  );
}
