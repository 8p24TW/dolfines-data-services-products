import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { proxyToPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const file = formData.get("file");
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "Missing charting file" }, { status: 400 });
    }

    const forward = new FormData();
    forward.append("file", file, file.name);
    forward.append("time_column", String(formData.get("time_column") ?? ""));
    forward.append("series", String(formData.get("series") ?? "[]"));
    forward.append("start_date", String(formData.get("start_date") ?? ""));
    forward.append("end_date", String(formData.get("end_date") ?? ""));
    forward.append("aggregation", String(formData.get("aggregation") ?? "hourly"));
    forward.append("site_timezone", String(formData.get("site_timezone") ?? "UTC"));
    const worksheet = String(formData.get("worksheet") ?? "").trim();
    if (worksheet) {
      forward.append("worksheet", worksheet);
    }

    const response = await proxyToPythonService("/charting", forward);
    return NextResponse.json(await response.json());
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to run charting" },
      { status: 500 }
    );
  }
}
