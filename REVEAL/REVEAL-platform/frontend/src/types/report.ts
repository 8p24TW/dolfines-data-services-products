export type ReportType = "comprehensive" | "daily" | "monthly";
export type ReportStatus = "queued" | "running" | "complete" | "error";

export interface ReportJob {
  jobId: string;
  siteId?: string;
  status: ReportStatus;
  progress: number; // 0-100
  pdfUrl?: string;
  error?: string;
  reportType?: ReportType;
  reportDate?: string;
  lang?: "en" | "fr" | "de";
  filename?: string;
}

export interface ReportMeta {
  id: string;
  siteId: string;
  reportType: ReportType;
  reportDate?: string; // ISO date (daily/monthly)
  generatedAt: string; // ISO datetime
  lang: "en" | "fr" | "de";
  filename: string;
  downloadUrl: string;
  sizeBytes?: number;
}

export interface GenerateReportRequest {
  siteId: string;
  reportType: ReportType;
  reportDate?: string;
  lang: "en" | "fr" | "de";
  columnMappings?: Record<string, ColumnMapping>;
}

export interface ColumnMapping {
  time?: string;
  power?: string[];
  irradiance?: string;
  temperature?: string;
  ambientTemperature?: string;
  moduleTemperature?: string;
  wind_speed?: string;
  wind_dir?: string;
  worksheet?: string;
}
