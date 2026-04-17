import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { mapReportJob } from "@/lib/server/site-mapper";

export const runtime = "nodejs";
export const maxDuration = 600; // 10-minute Vercel function timeout for SSE streaming

export async function GET(request: Request, context: { params: { jobId: string } }) {
  try {
    await getCurrentUserRecord();
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        let closed = false;

        const sendUpdate = async () => {
          if (closed) return;

          const job = await prisma.reportJob.findUnique({
            where: { id: context.params.jobId },
          });

          if (!job) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: "Job not found" })}\n\n`));
            closed = true;
            controller.close();
            return;
          }

          controller.enqueue(encoder.encode(`data: ${JSON.stringify(mapReportJob(job))}\n\n`));

          if (job.status === "complete" || job.status === "error") {
            closed = true;
            clearInterval(intervalId);
            controller.close();
          }
        };

        const intervalId = setInterval(() => {
          void sendUpdate();
        }, 1000);

        void sendUpdate();

        request.signal.addEventListener("abort", () => {
          if (closed) return;
          closed = true;
          clearInterval(intervalId);
          controller.close();
        });
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 });
    }
    return new Response(JSON.stringify({ error: "Failed to stream report job" }), { status: 500 });
  }
}
