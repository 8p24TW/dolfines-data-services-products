import { NextResponse } from "next/server";
import { loadSiteLongTermProfile } from "@/lib/server/market-site-profile";

export const runtime = "nodejs";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const siteId = url.searchParams.get("siteId");

    if (!siteId) {
      return NextResponse.json({ error: "siteId is required" }, { status: 400 });
    }

    const summary = await loadSiteLongTermProfile(siteId);

    return NextResponse.json({
      site_id: siteId,
      has_long_term_output: summary.hasLongTermOutput,
      latest_output_file: summary.latestOutputFile,
      latest_output_generated_at: summary.latestOutputGeneratedAt,
      average_annual_energy_mwh: summary.averageAnnualEnergyMwh,
      recommendation: summary.hasLongTermOutput
        ? "Long-term correlation output is available for this site and will be injected into the site-specific price and retrofit interpretation."
        : "No long-term correlation output was found for this site yet. Run the long-term modelling workflow first so REVEAL can use the site-specific production basis.",
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load site market context" },
      { status: 500 }
    );
  }
}
