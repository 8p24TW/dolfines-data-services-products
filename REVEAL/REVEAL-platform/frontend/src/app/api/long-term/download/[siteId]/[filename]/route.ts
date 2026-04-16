import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: { siteId: string; filename: string } }) {
  try {
    await getCurrentUserRecord();
    const filePath = path.join(process.cwd(), "generated-long-term", context.params.siteId, context.params.filename);
    const fileBuffer = await readFile(filePath);
    const extension = path.extname(context.params.filename).toLowerCase();
    const contentType = extension === ".xlsx" ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" : "text/csv; charset=utf-8";

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${context.params.filename}"`,
      },
    });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to download long-term output" }, { status: 404 });
  }
}
