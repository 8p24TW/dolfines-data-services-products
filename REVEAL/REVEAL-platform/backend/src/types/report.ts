export type ReportType = "comprehensive" | "daily" | "monthly";
export type ReportStatus = "queued" | "running" | "complete" | "error";

export interface ReportJob {
  jobId: string;
  status: ReportStatus;
  progress: number;
  pdfUrl?: string;
  error?: string;
}

export interface ReportMeta {
  id: string;
  siteId: string;
  reportType: ReportType;
  reportDate?: string;
  generatedAt: string;
  lang: "en" | "fr";
  filename: string;
  downloadUrl: string;
  sizeBytes?: number;
}
