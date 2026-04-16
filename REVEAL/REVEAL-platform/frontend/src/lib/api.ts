const API_BASE = "";

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export const api = {
  sites: {
    list: () => apiFetch<Site[]>("/api/sites"),
    get: (id: string) => apiFetch<Site>(`/api/sites/${id}`),
    create: (body: Record<string, unknown>) =>
      apiFetch<Site>("/api/sites", { method: "POST", body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" } }),
    update: (id: string, body: Record<string, unknown>) =>
      apiFetch<Site>(`/api/sites/${id}`, { method: "PUT", body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" } }),
    delete: (id: string) =>
      apiFetch<void>(`/api/sites/${id}`, { method: "DELETE" }),
  },
  reports: {
    createJob: (form: FormData) =>
      apiFetch<{ jobId: string; status: string }>("/api/reports/jobs", {
        method: "POST", body: form }),
    getJob: (jobId: string) =>
      apiFetch<ReportJob>(`/api/reports/jobs/${jobId}`),
    history: (siteId: string) =>
      apiFetch<ReportMeta[]>(`/api/reports/history/${siteId}`),
  },
  analysis: {
    detectColumns: (form: FormData) =>
      apiFetch<ColumnDetectionResult>("/api/analysis/detect-columns", {
        method: "POST", body: form }),
    run: (form: FormData) =>
      apiFetch<AnalysisResult>("/api/analysis/run", {
        method: "POST", body: form }),
  },
  charting: {
    dateRange: (form: FormData) =>
      apiFetch<ChartingDateRangeResult>("/api/charting/date-range", {
        method: "POST", body: form }),
    referenceIrradiance: (form: FormData) =>
      apiFetch<ChartingReferenceIrradianceResult>("/api/charting/reference-irradiance", {
        method: "POST", body: form }),
    run: (form: FormData) =>
      apiFetch<ChartingResult>("/api/charting/run", {
        method: "POST", body: form }),
  },
  longTerm: {
    fetchReference: (form: FormData) =>
      apiFetch<{
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
      }>("/api/long-term/reference", {
        method: "POST",
        body: form,
      }),
    createJob: (form: FormData) =>
      apiFetch<{ jobId: string; status: string }>("/api/long-term/jobs", {
        method: "POST",
        body: form,
      }),
    getJob: (jobId: string) =>
      apiFetch<LongTermCorrelationJob>(`/api/long-term/jobs/${jobId}`),
  },
  market: {
    priceForecast: (body: Record<string, unknown>) =>
      apiFetch<PriceForecastResult>("/api/market/price-forecast", {
        method: "POST",
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
      }),
    siteContext: (siteId: string) =>
      apiFetch<MarketSiteContext>(`/api/market/site-context?siteId=${encodeURIComponent(siteId)}`),
    retrofitBess: (body: Record<string, unknown>) =>
      apiFetch<RetrofitBessResult>("/api/market/retrofit-bess", {
        method: "POST",
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
      }),
    hourlyProfile: (params: { year: number; month: number; day_type: string; scenario: string }) =>
      apiFetch<HourlyProfileResult>(
        `/api/market/hourly-profile?year=${params.year}&month=${params.month}&day_type=${encodeURIComponent(params.day_type)}&scenario=${params.scenario}`
      ),
  },
  portal: {
    submit: (form: FormData) =>
      apiFetch<{ success: boolean; packageName: string }>("/api/portal/submit", {
        method: "POST", body: form }),
  },
};

// Import types for the api helper (resolved from @/types)
import type { Site } from "@/types/site";
import type { ReportJob, ReportMeta } from "@/types/report";
import type { AnalysisResult, ColumnDetectionResult } from "@/types/analysis";
import type { ChartingDateRangeResult, ChartingReferenceIrradianceResult, ChartingResult } from "@/types/charting";
import type { LongTermCorrelationJob } from "@/types/long-term";
import type { PriceForecastResult, RetrofitBessResult, HourlyProfileResult, MarketSiteContext } from "@/types/market";
