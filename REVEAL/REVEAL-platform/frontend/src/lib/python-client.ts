/**
 * Browser-side caller for the Railway Python analysis service.
 *
 * Large SCADA files (often 10–50 MB) exceed Vercel's 4.5 MB serverless-function
 * body limit, so the browser must post them directly to Railway rather than
 * proxying through the Next.js API routes.
 *
 * Set NEXT_PUBLIC_PYTHON_SERVICE_URL in Vercel to the public Railway service URL.
 * If the variable is absent, helpers fall back to the Vercel proxy routes so
 * local development continues to work without Railway access.
 */

import type { AnalysisResult, ColumnDetectionResult } from "@/types/analysis";
import type { Site } from "@/types/site";

const DIRECT_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_PYTHON_SERVICE_URL ?? "").replace(/\/$/, "")
    : "";

export function canCallDirectly(): boolean {
  return Boolean(DIRECT_URL);
}

async function directPost<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${DIRECT_URL}${path}`, {
    method: "POST",
    body: form,
    // No Content-Type — browser sets multipart boundary automatically
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Python service ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function proxyPost<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    body: form,
    credentials: "same-origin",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Detect columns in a SCADA file.
 * - Direct path (large files): browser → Railway /detect-columns
 * - Proxy path (fallback):     browser → Vercel /api/analysis/detect-columns → Railway
 */
export async function detectColumns(
  file: File,
  siteType: string,
  worksheet?: string,
): Promise<ColumnDetectionResult> {
  const form = new FormData();
  form.append("file", file, file.name);
  form.append("site_type", siteType);
  if (worksheet) form.append("worksheet", worksheet);

  if (canCallDirectly()) {
    return directPost<ColumnDetectionResult>("/detect-columns", form);
  }

  // Proxy path uses slightly different field names
  const proxyForm = new FormData();
  proxyForm.append("file", file, file.name);
  proxyForm.append("siteType", siteType);
  if (worksheet) proxyForm.append("worksheet", worksheet);
  return proxyPost<ColumnDetectionResult>("/api/analysis/detect-columns", proxyForm);
}

/**
 * Run the full analysis pipeline.
 * - Direct path (large files): browser → Railway /analyse
 * - Proxy path (fallback):     browser → Vercel /api/analysis/run → Railway
 */
export async function runAnalysis(
  files: File[],
  site: Site,
  columnMappings: Record<string, unknown>,
  siteConfigOverrides: Record<string, unknown>,
  lang = "en",
): Promise<AnalysisResult> {
  if (canCallDirectly()) {
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));
    form.append("site_config", JSON.stringify({ ...site, ...siteConfigOverrides }));
    form.append("column_mappings", JSON.stringify(columnMappings));
    form.append("lang", lang);
    return directPost<AnalysisResult>("/analyse", form);
  }

  // Proxy path: Vercel route reads site from DB using siteId
  const form = new FormData();
  form.append("siteId", site.id);
  form.append("columnMappings", JSON.stringify(columnMappings));
  form.append("siteConfigOverrides", JSON.stringify(siteConfigOverrides));
  files.forEach((f) => form.append("files", f));
  return proxyPost<AnalysisResult>("/api/analysis/run", form);
}
