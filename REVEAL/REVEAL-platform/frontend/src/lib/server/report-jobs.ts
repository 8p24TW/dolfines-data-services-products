import crypto from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { prisma } from "@/lib/prisma";
import { mapSite, mapSiteToAnalysisConfig } from "@/lib/server/site-mapper";
import { proxyToPythonService } from "@/lib/server/python-service";

type ReportJobPayload = {
  siteId: string;
  reportType: "comprehensive" | "daily" | "monthly";
  lang: "en" | "fr" | "de";
  reportDate?: string;
  columnMappings: Record<string, unknown>;
  siteConfigOverrides?: Record<string, unknown>;
  files: File[];
};

async function updateJob(jobId: string, data: {
  status?: "queued" | "running" | "complete" | "error";
  progress?: number;
  pdfUrl?: string | null;
  error?: string | null;
}) {
  await prisma.reportJob.update({
    where: { id: jobId },
    data,
  });
}

export async function startReportJob(payload: ReportJobPayload) {
  const id = crypto.randomUUID();

  await prisma.reportJob.create({
    data: {
      id,
      siteId: payload.siteId,
      reportType: payload.reportType,
      reportDate: payload.reportDate ? new Date(payload.reportDate) : null,
      lang: payload.lang,
      status: "queued",
      progress: 0,
    },
  });

  void runReportJob(id, payload);
  return id;
}

async function runReportJob(jobId: string, payload: ReportJobPayload) {
  try {
    await updateJob(jobId, { status: "running", progress: 10, error: null });

    const siteRecord = await prisma.site.findUnique({
      where: { id: payload.siteId },
      include: { solar_module_types: true },
    });

    if (!siteRecord) {
      throw new Error("Site not found");
    }

    const site = mapSite(siteRecord);
    const form = new FormData();
    payload.files.forEach((file) => form.append("files", file, file.name));
    form.append("site_config", JSON.stringify({ ...mapSiteToAnalysisConfig(site), ...(payload.siteConfigOverrides ?? {}) }));
    form.append("column_mappings", JSON.stringify(payload.columnMappings ?? {}));
    form.append("report_type", payload.reportType);
    form.append("lang", payload.lang);
    if (payload.reportDate) {
      form.append("report_date", payload.reportDate);
    }
    const outputFormat = payload.reportType === "daily" ? "html" : "pdf";
    form.append("output_format", outputFormat);

    await updateJob(jobId, { progress: 40 });
    const response = await proxyToPythonService("/report/generate", form);

    await updateJob(jobId, { progress: 85 });
    const fileBytes = Buffer.from(await response.arrayBuffer());
    const reportsDir = path.join(process.cwd(), "generated-reports", payload.siteId);
    await mkdir(reportsDir, { recursive: true });

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const extension = outputFormat === "html" ? "html" : "pdf";
    const filename = `${payload.siteId}_${payload.reportType}_${payload.lang}_${timestamp}.${extension}`;
    const outputPath = path.join(reportsDir, filename);
    await writeFile(outputPath, fileBytes);

    const downloadUrl = `/api/reports/download/${payload.siteId}/${filename}`;

    await prisma.report.create({
      data: {
        siteId: payload.siteId,
        reportType: payload.reportType,
        reportDate: payload.reportDate ? new Date(payload.reportDate) : null,
        lang: payload.lang,
        filename,
        downloadUrl,
        sizeBytes: fileBytes.byteLength,
      },
    });

    await updateJob(jobId, {
      status: "complete",
      progress: 100,
      pdfUrl: downloadUrl,
    });
  } catch (error) {
    await updateJob(jobId, {
      status: "error",
      progress: 100,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}
