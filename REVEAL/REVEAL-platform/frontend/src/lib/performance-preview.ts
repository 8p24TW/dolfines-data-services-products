"use client";

import type { AnalysisResult } from "@/types/analysis";

const STORAGE_PREFIX = "reveal:performance-preview:";

export interface PerformancePreviewSnapshot {
  siteId: string;
  generatedAt: string;
  dataDateRange: [string, string] | null;
  analysedDays: number | null;
  latestAnnualPrPct: number | null;
  meanAvailabilityPct: number;
  siteSpecificYieldAnnualizedKwhKwp: number | null;
  totalMeasuredEnergyMwh: number;
  wholeSiteEvents: number;
  powerDataPct: number;
  irradiancePct: number;
  recentMonthlyPr: Array<{
    month: string;
    PR_pct: number;
    irrad_kwh_m2: number;
  }>;
  topFindings: string[];
}

function average(values: number[]) {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function storageKey(siteId: string) {
  return `${STORAGE_PREFIX}${siteId}`;
}

function daysBetween(range: [string, string] | null | undefined) {
  if (!range?.[0] || !range?.[1]) return null;
  const start = new Date(range[0]);
  const end = new Date(range[1]);
  const diff = end.getTime() - start.getTime();
  if (!Number.isFinite(diff) || diff < 0) return null;
  return Math.max(diff / (1000 * 60 * 60 * 24), 0);
}

export function buildPerformancePreviewSnapshot(siteId: string, result: AnalysisResult): PerformancePreviewSnapshot {
  const latestAnnualPrPct =
    result.pr.annual.at(-1)?.PR_pct ?? average(result.pr.monthly.map((item) => item.PR_pct));
  const totalMeasuredEnergyMwh = result.pr.monthly.reduce((sum, item) => sum + item.E_act_mwh, 0);
  const analysedDays = daysBetween(result.summary.data_date_range ?? null);
  const siteSpecificYieldKwhKwp = result.summary.cap_dc_kwp > 0 ? (totalMeasuredEnergyMwh * 1000) / result.summary.cap_dc_kwp : null;
  const siteSpecificYieldAnnualizedKwhKwp =
    siteSpecificYieldKwhKwp != null && analysedDays && analysedDays > 0
      ? siteSpecificYieldKwhKwp * (365.25 / analysedDays)
      : siteSpecificYieldKwhKwp;

  return {
    siteId,
    generatedAt: new Date().toISOString(),
    dataDateRange: result.summary.data_date_range ?? null,
    analysedDays,
    latestAnnualPrPct: latestAnnualPrPct ?? null,
    meanAvailabilityPct: result.availability.mean_pct,
    siteSpecificYieldAnnualizedKwhKwp,
    totalMeasuredEnergyMwh,
    wholeSiteEvents: result.availability.whole_site_events,
    powerDataPct: result.data_quality.overall_power_pct,
    irradiancePct: result.data_quality.irradiance_pct,
    recentMonthlyPr: result.pr.monthly.slice(-6).map((item) => ({
      month: item.month,
      PR_pct: item.PR_pct,
      irrad_kwh_m2: item.irrad_kwh_m2,
    })),
    topFindings: result.punchlist.slice(0, 3).map((item) => item.finding),
  };
}

export function savePerformancePreviewSnapshot(siteId: string, result: AnalysisResult) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey(siteId), JSON.stringify(buildPerformancePreviewSnapshot(siteId, result)));
}

export function loadPerformancePreviewSnapshot(siteId: string): PerformancePreviewSnapshot | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(storageKey(siteId));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PerformancePreviewSnapshot;
  } catch {
    window.localStorage.removeItem(storageKey(siteId));
    return null;
  }
}

export function clearPerformancePreviewSnapshot(siteId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(storageKey(siteId));
}
