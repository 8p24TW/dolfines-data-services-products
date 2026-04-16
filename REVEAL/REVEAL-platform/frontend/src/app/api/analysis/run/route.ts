import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { mapSite, mapSiteToAnalysisConfig } from "@/lib/server/site-mapper";
import { proxyToPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const siteId = String(formData.get("siteId") ?? "");
    const columnMappings = String(formData.get("columnMappings") ?? "{}");
    const siteConfigOverridesRaw = String(formData.get("siteConfigOverrides") ?? "{}");
    const files = formData.getAll("files").filter((item): item is File => item instanceof File);

    if (!siteId || files.length === 0) {
      return NextResponse.json({ error: "Missing site or files" }, { status: 400 });
    }

    const siteRecord = await prisma.site.findUnique({
      where: { id: siteId },
      include: { solar_module_types: true },
    });

    if (!siteRecord) {
      return NextResponse.json({ error: "Site not found" }, { status: 404 });
    }

    const site = mapSite(siteRecord);
    const siteConfigOverrides = JSON.parse(siteConfigOverridesRaw);
    const forward = new FormData();
    files.forEach((file) => forward.append("files", file, file.name));
    forward.append("site_config", JSON.stringify({ ...mapSiteToAnalysisConfig(site), ...siteConfigOverrides }));
    forward.append("column_mappings", columnMappings);

    const response = await proxyToPythonService("/analyse", forward);
    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("POST /api/analysis/run failed", error);
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to run analysis" },
      { status: 500 }
    );
  }
}
