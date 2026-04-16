import { NextResponse } from "next/server";
import { getFromPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const year = url.searchParams.get("year") ?? "2030";
    const month = url.searchParams.get("month") ?? "6";
    const day_type = url.searchParams.get("day_type") ?? "ouvre";
    const scenario = url.searchParams.get("scenario") ?? "base";

    const response = await getFromPythonService("/market/hourly-profile", {
      year,
      month,
      day_type,
      scenario,
    });
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to load hourly profile" },
      { status: 500 }
    );
  }
}
