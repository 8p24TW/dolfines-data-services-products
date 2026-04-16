"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { ReportHistoryTable } from "@/components/reports/ReportHistoryTable";
import { useSite } from "@/hooks/useSites";
import { BackLink } from "@/components/layout/BackLink";
import { useTranslation } from "@/lib/i18n";

export default function ReportHistoryPage({ params }: { params: { siteId: string } }) {
  const { t } = useTranslation();
  const { site } = useSite(params.siteId);

  const { data: reports = [], isLoading } = useSWR(
    ["report-history", params.siteId],
    ([, id]) => api.reports.history(id)
  );

  return (
    <div className="space-y-4">
      <BackLink href={`/dashboard/site/${params.siteId}/reports`} label={t("common.backToReporting")} />
      <h1 className="font-dolfines text-2xl font-semibold tracking-[0.08em] text-white">
        {t("reports.history")} {site ? `· ${site.display_name}` : ""}
      </h1>
      {isLoading ? (
        <p className="text-sm text-slate-400">{t("common.loading")}</p>
      ) : (
        <div className="rounded-xl border border-navy-light bg-navy-DEFAULT/60 p-5">
          <ReportHistoryTable reports={reports} />
        </div>
      )}
    </div>
  );
}
