import { Router } from "express";
import JSZip from "jszip";
import { upload } from "../middleware/upload";
import { sharepointService } from "../services/sharepointService";

const router = Router();

// Public endpoint — no auth required
router.post("/submit", upload.any(), async (req, res) => {
  const files = req.files as Express.Multer.File[];
  const metadata = req.body.metadata ? JSON.parse(req.body.metadata as string) : req.body;

  try {
    const zip = new JSZip();

    // Add metadata
    zip.file("submission_metadata.json", JSON.stringify(metadata, null, 2));

    // Organize files by role inferred from field name
    // Expected field names: site_0_inverter, site_0_irradiance, site_0_other, etc.
    for (const file of files) {
      const match = file.fieldname.match(/^site_(\d+)_(\w+)$/);
      if (match) {
        const [, siteIdx, role] = match;
        const siteName = metadata[`site_${siteIdx}_name`] ?? `site_${siteIdx}`;
        zip.file(`${siteName}/${role}/${file.originalname}`, require("fs").readFileSync(file.path));
      }
    }

    const zipBuffer = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
    const pkgName = `REVEAL_submission_${Date.now()}.zip`;

    // Try SharePoint upload; fall back to sending the ZIP directly
    let sharePointUrl: string | null = null;
    try {
      sharePointUrl = await sharepointService.uploadFile("Partage client/submissions", zipBuffer, pkgName);
    } catch {
      // SharePoint not configured — that's OK for dev
    }

    res.json({ success: true, packageName: pkgName, sharePointUrl });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

export default router;
