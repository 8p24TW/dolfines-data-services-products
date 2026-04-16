import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { startReportJob } from "@/lib/server/report-jobs";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const siteId = String(formData.get("siteId") ?? "");
    const reportType = String(formData.get("reportType") ?? "comprehensive") as "comprehensive" | "daily" | "monthly";
    const lang = String(formData.get("lang") ?? "en") as "en" | "fr" | "de";
    const reportDate = formData.get("reportDate");
    const columnMappingsRaw = String(formData.get("columnMappings") ?? "{}");
    const siteConfigOverridesRaw = String(formData.get("siteConfigOverrides") ?? "{}");
    const files = formData.getAll("files").filter((item): item is File => item instanceof File);

    if (!siteId || files.length === 0) {
      return NextResponse.json({ error: "Missing site or files" }, { status: 400 });
    }

    const jobId = await startReportJob({
      siteId,
      reportType,
      lang,
      reportDate: reportDate ? String(reportDate) : undefined,
      columnMappings: JSON.parse(columnMappingsRaw),
      siteConfigOverrides: JSON.parse(siteConfigOverridesRaw),
      files,
    });

    return NextResponse.json({ jobId, status: "queued" }, { status: 202 });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to create report job" }, { status: 500 });
  }
}
