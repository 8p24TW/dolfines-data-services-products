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
    const worksheet = String(formData.get("worksheet") ?? "").trim();
    if (worksheet) {
      forward.append("worksheet", worksheet);
    }

    const response = await proxyToPythonService("/charting/date-range", forward);
    return NextResponse.json(await response.json());
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to detect charting date range" },
      { status: 500 }
    );
  }
}
