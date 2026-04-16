import { NextResponse } from "next/server";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { readLongTermJob } from "@/lib/server/long-term-jobs";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: { jobId: string } }) {
  try {
    await getCurrentUserRecord();
    const job = readLongTermJob(context.params.jobId);

    if (!job) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json(job);
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to load long-term job" }, { status: 500 });
  }
}
