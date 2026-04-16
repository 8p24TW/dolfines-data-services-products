import { Queue, Worker, Job } from "bullmq";
import { Redis } from "ioredis";
import crypto from "crypto";
import fs from "fs";
import path from "path";
import type { ReportJob, ReportMeta } from "../types/report";
import { analysisService } from "./analysisService";
import { sharepointService } from "./sharepointService";
import { siteService } from "./siteService";

const connection = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  maxRetriesPerRequest: null,
});

export const reportQueue = new Queue("reports", { connection });

// In-memory job status (survives within process lifetime; use Redis for multi-instance)
const jobStore = new Map<string, ReportJob>();

export function getJobStatus(jobId: string): ReportJob | null {
  return jobStore.get(jobId) ?? null;
}

export function createJob(jobId: string) {
  const job: ReportJob = { jobId, status: "queued", progress: 0 };
  jobStore.set(jobId, job);
  return job;
}

function updateJob(jobId: string, patch: Partial<ReportJob>) {
  const existing = jobStore.get(jobId);
  if (existing) jobStore.set(jobId, { ...existing, ...patch });
}

// SSE subscribers
const subscribers = new Map<string, Set<(data: ReportJob) => void>>();

export function subscribeJob(jobId: string, cb: (data: ReportJob) => void) {
  if (!subscribers.has(jobId)) subscribers.set(jobId, new Set());
  subscribers.get(jobId)!.add(cb);
  return () => subscribers.get(jobId)?.delete(cb);
}

function emit(jobId: string, data: ReportJob) {
  subscribers.get(jobId)?.forEach((cb) => cb(data));
}

function setProgress(jobId: string, progress: number, status?: ReportJob["status"]) {
  updateJob(jobId, { progress, ...(status ? { status } : {}) });
  const job = jobStore.get(jobId)!;
  emit(jobId, job);
}

// Worker
new Worker<{ jobId: string; siteId: string; reportType: string; lang: string; reportDate?: string; tmpFiles: string[]; originalNames: string[]; columnMappings: object }>(
  "reports",
  async (job: Job) => {
    const { jobId, siteId, reportType, lang, reportDate, tmpFiles, originalNames, columnMappings } = job.data as {
      jobId: string; siteId: string; reportType: string; lang: string;
      reportDate?: string; tmpFiles: string[]; originalNames: string[];
      columnMappings: object;
    };

    try {
      setProgress(jobId, 5, "running");

      const site = siteService.getById(siteId);
      if (!site) throw new Error(`Site ${siteId} not found`);

      const files = tmpFiles.map((p, i) => ({ path: p, originalname: originalNames[i] }));

      setProgress(jobId, 20);

      const pdfBuffer = await analysisService.generateReport(
        files, site, columnMappings, reportType, lang, reportDate
      );

      setProgress(jobId, 80);

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 16);
      const filename = `REVEAL_${reportType}_${siteId}_${timestamp}.pdf`;

      // Upload PDF to SharePoint
      let downloadUrl = "";
      try {
        await sharepointService.uploadFile(`repat_platform/reports/${siteId}`, pdfBuffer, filename);
        downloadUrl = `/api/reports/download/${siteId}/${filename}`;
      } catch (spErr) {
        console.warn("SharePoint upload failed, saving locally:", spErr);
        const localDir = path.join(process.cwd(), "reports", siteId);
        fs.mkdirSync(localDir, { recursive: true });
        fs.writeFileSync(path.join(localDir, filename), pdfBuffer);
        downloadUrl = `/api/reports/download/${siteId}/${filename}`;
      }

      // Update report history
      const meta: ReportMeta = {
        id: crypto.randomUUID(),
        siteId,
        reportType: reportType as ReportMeta["reportType"],
        reportDate,
        generatedAt: new Date().toISOString(),
        lang: lang as "en" | "fr",
        filename,
        downloadUrl,
        sizeBytes: pdfBuffer.byteLength,
      };

      // Cleanup tmp files
      tmpFiles.forEach((f) => { try { fs.unlinkSync(f); } catch {} });

      setProgress(jobId, 100, "complete");
      updateJob(jobId, { pdfUrl: downloadUrl });
      emit(jobId, jobStore.get(jobId)!);

      return meta;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      updateJob(jobId, { status: "error", error: msg });
      emit(jobId, jobStore.get(jobId)!);
      throw err;
    }
  },
  { connection, concurrency: parseInt(process.env.REPORT_JOB_CONCURRENCY ?? "2", 10) }
);
