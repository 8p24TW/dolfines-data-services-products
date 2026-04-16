import { Router, type Response } from "express";
import crypto from "crypto";
import path from "path";
import fs from "fs";
import { requireAuth, type AuthRequest } from "../middleware/auth";
import { upload } from "../middleware/upload";
import { reportQueue, getJobStatus, createJob, subscribeJob } from "../services/reportJobService";

const router = Router();

// Create a report generation job
router.post("/jobs", requireAuth, upload.array("files"), async (req: AuthRequest, res) => {
  const files = req.files as Express.Multer.File[];
  if (!files?.length) return res.status(400).json({ error: "No files uploaded" });

  const { siteId, reportType, lang = "en", reportDate, columnMappings } = req.body as {
    siteId: string; reportType: string; lang?: string; reportDate?: string; columnMappings?: string;
  };

  const jobId = crypto.randomUUID();
  createJob(jobId);

  await reportQueue.add("generate", {
    jobId,
    siteId,
    reportType,
    lang,
    reportDate,
    columnMappings: columnMappings ? JSON.parse(columnMappings) : {},
    tmpFiles: files.map((f) => f.path),
    originalNames: files.map((f) => f.originalname),
  });

  res.status(202).json({ jobId, status: "queued" });
});

// Poll job status
router.get("/jobs/:jobId", requireAuth, (req, res) => {
  const job = getJobStatus(req.params.jobId);
  if (!job) return res.status(404).json({ error: "Job not found" });
  res.json(job);
});

// SSE stream for live progress
router.get("/jobs/:jobId/stream", (req, res: Response) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const { jobId } = req.params;

  // Send current status immediately
  const current = getJobStatus(jobId);
  if (current) res.write(`data: ${JSON.stringify(current)}\n\n`);

  const unsubscribe = subscribeJob(jobId, (data) => {
    res.write(`data: ${JSON.stringify(data)}\n\n`);
    if (data.status === "complete" || data.status === "error") {
      res.end();
    }
  });

  req.on("close", unsubscribe);
});

// Download report (proxy from local storage or SharePoint)
router.get("/download/:siteId/:filename", requireAuth, (req, res) => {
  const { siteId, filename } = req.params;
  const localPath = path.join(process.cwd(), "reports", siteId, filename);
  if (fs.existsSync(localPath)) {
    return res.download(localPath, filename);
  }
  res.status(404).json({ error: "Report not found" });
});

// Report history per site
router.get("/history/:siteId", requireAuth, async (_req, res) => {
  // TODO: load from SharePoint report_history.json; returning empty for now
  res.json([]);
});

export default router;
