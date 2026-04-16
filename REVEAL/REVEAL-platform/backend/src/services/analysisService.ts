import axios from "axios";
import FormData from "form-data";
import fs from "fs";

const PYTHON_URL = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8000";

export const analysisService = {
  async detectColumns(filePath: string, originalName: string, siteType: string) {
    const form = new FormData();
    form.append("file", fs.createReadStream(filePath), { filename: originalName });
    form.append("site_type", siteType);

    const { data } = await axios.post(`${PYTHON_URL}/detect-columns`, form, {
      headers: form.getHeaders(),
      timeout: 30_000,
    });
    return data;
  },

  async runAnalysis(
    files: Array<{ path: string; originalname: string }>,
    siteConfig: object,
    columnMappings: object,
    lang = "en"
  ) {
    const form = new FormData();
    files.forEach((f) => form.append("files", fs.createReadStream(f.path), { filename: f.originalname }));
    form.append("site_config", JSON.stringify(siteConfig));
    form.append("column_mappings", JSON.stringify(columnMappings));
    form.append("lang", lang);

    const { data } = await axios.post(`${PYTHON_URL}/analyse`, form, {
      headers: form.getHeaders(),
      timeout: 300_000, // 5 min
    });
    return data;
  },

  async generateReport(
    files: Array<{ path: string; originalname: string }>,
    siteConfig: object,
    columnMappings: object,
    reportType: string,
    lang: string,
    reportDate?: string
  ): Promise<Buffer> {
    const form = new FormData();
    files.forEach((f) => form.append("files", fs.createReadStream(f.path), { filename: f.originalname }));
    form.append("site_config", JSON.stringify(siteConfig));
    form.append("column_mappings", JSON.stringify(columnMappings));
    form.append("report_type", reportType);
    form.append("lang", lang);
    if (reportDate) form.append("report_date", reportDate);

    const { data } = await axios.post<Buffer>(`${PYTHON_URL}/report/generate`, form, {
      headers: form.getHeaders(),
      responseType: "arraybuffer",
      timeout: 600_000, // 10 min
    });
    return Buffer.from(data);
  },
};
