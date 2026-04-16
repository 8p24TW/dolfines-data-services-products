import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";

import sitesRouter from "./routes/sites";
import reportsRouter from "./routes/reports";
import portalRouter from "./routes/portal";
import analysisRouter from "./routes/analysis";

const app = express();
const PORT = process.env.PORT ?? 3001;

app.use(helmet());
app.use(cors({ origin: process.env.NEXTAUTH_URL ?? "http://localhost:3000", credentials: true }));
app.use(morgan("dev"));
app.use(express.json());

// Routes
app.use("/api/sites", sitesRouter);
app.use("/api/reports", reportsRouter);
app.use("/api/portal", portalRouter);
app.use("/api/analysis", analysisRouter);

// Health
app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});

export default app;
