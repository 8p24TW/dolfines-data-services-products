"use client";

import { useReportJob } from "@/hooks/useReportJob";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/lib/i18n";

interface ReportProgressProps {
  jobId: string;
}

const API_BASE = "";

export function ReportProgress({ jobId }: ReportProgressProps) {
  const { t } = useTranslation();
  const job = useReportJob(jobId);

  if (!job) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        Connecting…
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-300 capitalize">{job.status}</span>
        <span className="text-slate-400">{job.progress}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-navy-light overflow-hidden">
        <div
          className="h-full rounded-full bg-orange-DEFAULT transition-all duration-500"
          style={{ width: `${job.progress}%` }}
        />
      </div>

      {job.status === "complete" && job.pdfUrl && (
        <a
          href={`${API_BASE}${job.pdfUrl}`}
          download
          className="inline-block"
        >
          <Button variant="primary" size="sm">
            {t("reports.download")}
          </Button>
        </a>
      )}

      {job.status === "error" && (
        <p className="text-xs text-danger">{job.error ?? "Report generation failed."}</p>
      )}
    </div>
  );
}
