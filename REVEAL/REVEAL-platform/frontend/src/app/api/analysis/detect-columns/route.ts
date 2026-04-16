import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { proxyToPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const file = formData.get("file");
    const siteType = String(formData.get("siteType") ?? formData.get("site_type") ?? "solar");

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    const forward = new FormData();
    forward.append("file", file, file.name);
    forward.append("site_type", siteType);
    const worksheet = String(formData.get("worksheet") ?? "").trim();
    if (worksheet) {
      forward.append("worksheet", worksheet);
    }

    const response = await proxyToPythonService("/detect-columns", forward);
    return NextResponse.json(await response.json());
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to detect columns" }, { status: 500 });
  }
}
