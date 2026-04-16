import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { startLongTermJob } from "@/lib/server/long-term-jobs";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const siteId = String(formData.get("siteId") ?? "");
    const siteType = String(formData.get("siteType") ?? "solar") as "solar" | "wind";
    const source = String(formData.get("source") ?? "era5-land");
    const latitude = String(formData.get("latitude") ?? "");
    const longitude = String(formData.get("longitude") ?? "");
    const siteTimezone = String(formData.get("siteTimezone") ?? "UTC");
    const startDate = String(formData.get("startDate") ?? "2023-01-01");
    const endDate = String(formData.get("endDate") ?? "2024-12-31");
    const correlationYears = String(formData.get("correlationYears") ?? "20");
    const dcCapacityKwp = String(formData.get("dcCapacityKwp") ?? "");
    const acCapacityKw = String(formData.get("acCapacityKw") ?? "");
    const specificYieldKwhKwp = String(formData.get("specificYieldKwhKwp") ?? "");
    const yieldScenario = String(formData.get("yieldScenario") ?? "measured");
    const runMode = String(formData.get("runMode") ?? "projection") as "screening" | "preview" | "projection";
    const irradianceBasis = String(formData.get("irradianceBasis") ?? "poa");
    const trackerMode = String(formData.get("trackerMode") ?? "fixed-tilt");
    const irradianceTiltDeg = String(formData.get("irradianceTiltDeg") ?? "0");
    const outputFormat = String(formData.get("outputFormat") ?? "csv") as "csv" | "xlsx";
    const columnMappingsRaw = String(formData.get("columnMappings") ?? "{}");
    const files = formData.getAll("files").filter((item): item is File => item instanceof File);

    if (!siteId || files.length === 0 || !latitude || !longitude) {
      return NextResponse.json({ error: "Missing site, coordinates, or measured file" }, { status: 400 });
    }

    const jobId = await startLongTermJob({
      siteId,
      siteType,
      source,
      latitude,
      longitude,
      siteTimezone,
      startDate,
      endDate,
      correlationYears,
      dcCapacityKwp,
      acCapacityKw,
      specificYieldKwhKwp,
      yieldScenario,
      runMode,
      irradianceBasis,
      trackerMode,
      irradianceTiltDeg,
      outputFormat,
      columnMappings: JSON.parse(columnMappingsRaw),
      files,
    });

    return NextResponse.json({ jobId, status: "queued" }, { status: 202 });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to start long-term job" },
      { status: 500 }
    );
  }
}
