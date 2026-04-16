import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { mapReport } from "@/lib/server/site-mapper";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: { siteId: string } }) {
  try {
    await getCurrentUserRecord();
    const reports = await prisma.report.findMany({
      where: { siteId: context.params.siteId },
      orderBy: { generatedAt: "desc" },
    });

    return NextResponse.json(reports.map(mapReport));
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to load report history" }, { status: 500 });
  }
}
