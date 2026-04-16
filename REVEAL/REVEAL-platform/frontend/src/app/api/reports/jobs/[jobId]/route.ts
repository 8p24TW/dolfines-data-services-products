import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { mapReportJob } from "@/lib/server/site-mapper";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: { jobId: string } }) {
  try {
    await getCurrentUserRecord();
    const job = await prisma.reportJob.findUnique({
      where: { id: context.params.jobId },
    });

    if (!job) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json(mapReportJob(job));
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to load report job" }, { status: 500 });
  }
}
