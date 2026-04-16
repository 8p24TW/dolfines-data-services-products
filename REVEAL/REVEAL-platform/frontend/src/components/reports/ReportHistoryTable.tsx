"use client";

import { format } from "date-fns";
import type { ReportMeta } from "@/types/report";

interface ReportHistoryTableProps {
  reports: ReportMeta[];
}

const API_BASE = "";

export function ReportHistoryTable({ reports }: ReportHistoryTableProps) {
  if (reports.length === 0) {
    return <p className="text-sm text-slate-400">No reports generated yet.</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-navy-light text-left text-xs text-slate-400">
          <th className="pb-2 pr-4">Generated</th>
          <th className="pb-2 pr-4">Type</th>
          <th className="pb-2 pr-4">Lang</th>
          <th className="pb-2">Download</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-navy-light/40">
        {reports.map((r) => (
          <tr key={r.id} className="text-slate-300">
            <td className="py-2 pr-4 text-xs">
              {format(new Date(r.generatedAt), "dd MMM yyyy HH:mm")}
            </td>
            <td className="py-2 pr-4 capitalize">{r.reportType}</td>
            <td className="py-2 pr-4 uppercase text-xs">{r.lang}</td>
            <td className="py-2">
              <a
                href={`${API_BASE}${r.downloadUrl}`}
                download
                className="text-orange-DEFAULT hover:underline text-xs"
              >
                PDF
              </a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
