import { NextResponse } from "next/server";
import { postJsonToPythonService } from "@/lib/server/python-service";
import { loadSiteLongTermProfile } from "@/lib/server/market-site-profile";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const siteId = typeof body.site_id === "string" ? body.site_id : null;

    if (siteId) {
      const summary = await loadSiteLongTermProfile(siteId);
      body.site_profile_basis = summary.hasLongTermOutput ? "site-long-term" : "site-generic";
      if (summary.hasLongTermOutput) {
        body.site_profile_weights = summary.profileWeights;
        body.annual_production_mwh = summary.averageAnnualEnergyMwh ?? body.annual_production_mwh ?? null;
      }
    }

    const response = await postJsonToPythonService("/market/price-forecast", body);
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to run price forecast" },
      { status: 500 }
    );
  }
}
