import crypto from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { proxyToPythonService } from "@/lib/server/python-service";
import type { LongTermCorrelationJob } from "@/types/long-term";

type StartLongTermJobPayload = {
  siteId: string;
  siteType: "solar" | "wind";
  source: string;
  latitude: string;
  longitude: string;
  siteTimezone: string;
  startDate: string;
  endDate: string;
  correlationYears: string;
  dcCapacityKwp: string;
  acCapacityKw: string;
  specificYieldKwhKwp: string;
  yieldScenario: string;
  runMode: "screening" | "preview" | "projection";
  irradianceBasis: string;
  trackerMode: string;
  irradianceTiltDeg: string;
  outputFormat: "csv" | "xlsx";
  columnMappings: Record<string, unknown>;
  files: File[];
};

type JobStore = Map<string, LongTermCorrelationJob>;

declare global {
  // eslint-disable-next-line no-var
  var __revealLongTermJobs: JobStore | undefined;
}

function getStore(): JobStore {
  if (!global.__revealLongTermJobs) {
    global.__revealLongTermJobs = new Map();
  }
  return global.__revealLongTermJobs;
}

function getJob(jobId: string) {
  return getStore().get(jobId);
}

function setJob(jobId: string, job: LongTermCorrelationJob) {
  getStore().set(jobId, job);
}

function updateJob(jobId: string, patch: Partial<LongTermCorrelationJob>) {
  const existing = getJob(jobId);
  if (!existing) return;
  setJob(jobId, { ...existing, ...patch });
}

export function readLongTermJob(jobId: string) {
  return getJob(jobId);
}

export async function startLongTermJob(payload: StartLongTermJobPayload) {
  const id = crypto.randomUUID();
  setJob(id, {
    jobId: id,
    siteId: payload.siteId,
    status: "queued",
    runMode: payload.runMode,
    progress: 0,
    stage: "Queued",
    outputFormat: payload.outputFormat,
  });
  void runLongTermJob(id, payload);
  return id;
}

async function runLongTermJob(jobId: string, payload: StartLongTermJobPayload) {
  let progressTimer: NodeJS.Timeout | null = null;

  try {
    updateJob(jobId, {
      status: "running",
      runMode: payload.runMode,
      progress: 8,
      stage:
        payload.runMode === "screening"
          ? "Preparing bad-data screening"
          : payload.runMode === "preview"
            ? "Preparing fit-and-yield review"
            : "Preparing modelling inputs",
      error: undefined,
    });

    const firstFile = payload.files[0];
    if (!firstFile) {
      throw new Error("No measured data file was provided for long-term correlation.");
    }

    const form = new FormData();
    form.append("file", firstFile, firstFile.name);
    form.append("site_type", payload.siteType);
    form.append("source", payload.source);
    form.append("latitude", payload.latitude);
    form.append("longitude", payload.longitude);
    form.append("site_timezone", payload.siteTimezone);
    form.append("start_date", payload.startDate);
    form.append("end_date", payload.endDate);
    form.append("correlation_years", payload.correlationYears);
    form.append("dc_capacity_kwp", payload.dcCapacityKwp);
    form.append("ac_capacity_kw", payload.acCapacityKw);
    form.append("specific_yield_kwh_kwp", payload.specificYieldKwhKwp);
    form.append("yield_scenario", payload.yieldScenario);
    form.append("run_mode", payload.runMode);
    form.append("irradiance_basis", payload.irradianceBasis);
    form.append("tracker_mode", payload.trackerMode);
    form.append("irradiance_tilt_deg", payload.irradianceTiltDeg);
    form.append("column_mappings", JSON.stringify(payload.columnMappings));

    updateJob(jobId, {
      progress: 18,
      stage:
        payload.runMode === "screening"
          ? "Scanning measured data for repeated power values"
          : payload.runMode === "preview"
            ? "Analysing fit, irradiance correlation, and yield"
            : "Analysing reference weather and calibrating overlap period",
    });

    let syntheticProgress = 18;
    progressTimer = setInterval(() => {
      syntheticProgress = Math.min(syntheticProgress + 4, 74);
      updateJob(jobId, {
        progress: syntheticProgress,
        stage:
          payload.runMode === "screening"
            ? syntheticProgress < 46
              ? "Checking raw measured power channels"
              : "Compiling bad-data screening summary"
            : payload.runMode === "preview"
            ? syntheticProgress < 42
              ? "Analysing reference weather"
              : "Building fit and yield preview"
            : syntheticProgress < 40
              ? "Analysing reference weather"
              : "Running long-term correlation",
      });
    }, 1200);

    const response = await proxyToPythonService("/long-term/correlate", form);
    const result = (await response.json()) as {
      summary: LongTermCorrelationJob["summary"];
      charts: LongTermCorrelationJob["charts"];
      csvContent: string;
      csvFileName: string;
    };

    if (progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
    }

    if (payload.runMode === "screening") {
      updateJob(jobId, {
        status: "complete",
        progress: 100,
        stage: "Bad-data screening complete",
        summary: result.summary,
        charts: result.charts,
      });
      return;
    }

    if (payload.runMode === "preview") {
      updateJob(jobId, {
        status: "complete",
        progress: 100,
        stage: "Fit and yield review complete",
        summary: result.summary,
        charts: result.charts,
      });
      return;
    }

    updateJob(jobId, {
      progress: 82,
      stage: "Packaging long-term output for download",
    });

    const baseDir = path.join(process.cwd(), "generated-long-term", payload.siteId);
    await mkdir(baseDir, { recursive: true });

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const csvName = `${path.parse(result.csvFileName).name}_${timestamp}.csv`;
    const outputPath = path.join(baseDir, csvName);
    await writeFile(outputPath, result.csvContent, "utf-8");

    const note =
      payload.outputFormat === "xlsx"
        ? "CSV export generated. Native XLSX packaging will be added in the next iteration."
        : undefined;

    updateJob(jobId, {
      status: "complete",
      progress: 100,
      stage: "Long-term projection complete",
      downloadUrl: `/api/long-term/download/${payload.siteId}/${csvName}`,
      fileName: csvName,
      summary: result.summary ? { ...result.summary, note } : undefined,
      charts: result.charts,
    });
  } catch (error) {
    if (progressTimer) {
      clearInterval(progressTimer);
    }
    updateJob(jobId, {
      status: "error",
      progress: 100,
      stage:
        payload.runMode === "screening"
          ? "Bad-data screening failed"
          : payload.runMode === "preview"
            ? "Fit and yield review failed"
            : "Long-term correlation failed",
      error: error instanceof Error ? error.message : String(error),
    });
  }
}
