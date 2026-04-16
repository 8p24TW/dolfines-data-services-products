import { Router } from "express";
import { requireAuth } from "../middleware/auth";
import { upload } from "../middleware/upload";
import { analysisService } from "../services/analysisService";
import { siteService } from "../services/siteService";

const router = Router();

router.post("/detect-columns", requireAuth, upload.single("file"), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });
  const siteType = (req.body.siteType as string) ?? "solar";
  try {
    const result = await analysisService.detectColumns(req.file.path, req.file.originalname, siteType);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

router.post("/run", requireAuth, upload.array("files"), async (req, res) => {
  const files = req.files as Express.Multer.File[];
  if (!files?.length) return res.status(400).json({ error: "No files uploaded" });

  const { siteId, columnMappings } = req.body as { siteId: string; columnMappings: string };
  const site = siteService.getById(siteId);
  if (!site) return res.status(404).json({ error: "Site not found" });

  try {
    const result = await analysisService.runAnalysis(
      files.map((f) => ({ path: f.path, originalname: f.originalname })),
      site,
      columnMappings ? JSON.parse(columnMappings) : {}
    );
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

export default router;
