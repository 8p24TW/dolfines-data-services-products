import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { proxyToPythonService } from "@/lib/server/python-service";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    await getCurrentUserRecord();
    const formData = await request.formData();
    const forward = new FormData();

    for (const [key, value] of formData.entries()) {
      if (typeof value === "string") {
        forward.append(key, value);
      }
    }

    const response = await proxyToPythonService("/long-term/reference", forward);
    return NextResponse.json(await response.json());
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch reference weather" },
      { status: 500 }
    );
  }
}
