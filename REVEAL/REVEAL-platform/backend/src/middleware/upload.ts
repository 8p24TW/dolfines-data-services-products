import multer from "multer";
import path from "path";
import fs from "fs";

const TMP_DIR = process.env.UPLOAD_TMP_DIR ?? "/tmp/reveal-uploads";
const MAX_MB = parseInt(process.env.MAX_UPLOAD_SIZE_MB ?? "500", 10);

if (!fs.existsSync(TMP_DIR)) {
  fs.mkdirSync(TMP_DIR, { recursive: true });
}

export const upload = multer({
  dest: TMP_DIR,
  limits: { fileSize: MAX_MB * 1024 * 1024 },
  fileFilter(_req, file, cb) {
    const allowed = [".csv", ".xlsx", ".xls", ".pdf", ".zip", ".json"];
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, allowed.includes(ext));
  },
});
