import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: { siteId: string; filename: string } }) {
  try {
    const filePath = path.join(process.cwd(), "generated-reports", context.params.siteId, context.params.filename);
    const fileBuffer = await readFile(filePath);
    const contentType = context.params.filename.endsWith(".html")
      ? "text/html; charset=utf-8"
      : "application/pdf";
    return new Response(fileBuffer, {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${context.params.filename}"`,
      },
    });
  } catch {
    return new Response(JSON.stringify({ error: "Report not found" }), { status: 404 });
  }
}
