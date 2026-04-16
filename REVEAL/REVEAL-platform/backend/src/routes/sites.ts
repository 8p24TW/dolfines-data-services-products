import { Router } from "express";
import { requireAuth, type AuthRequest } from "../middleware/auth";
import { siteService } from "../services/siteService";

const router = Router();

router.get("/", requireAuth, (req: AuthRequest, res) => {
  const sites = siteService.listForUser(req.user!.oid);
  res.json(sites);
});

router.get("/:id", requireAuth, (req: AuthRequest, res) => {
  const site = siteService.getById(req.params.id);
  if (!site) return res.status(404).json({ error: "Site not found" });
  res.json(site);
});

router.post("/", requireAuth, (req: AuthRequest, res) => {
  const site = siteService.create(req.body, req.user!.oid);
  res.status(201).json(site);
});

router.put("/:id", requireAuth, (req: AuthRequest, res) => {
  const site = siteService.update(req.params.id, req.body);
  if (!site) return res.status(404).json({ error: "Site not found" });
  res.json(site);
});

router.delete("/:id", requireAuth, (req: AuthRequest, res) => {
  const ok = siteService.delete(req.params.id);
  if (!ok) return res.status(404).json({ error: "Site not found" });
  res.status(204).end();
});

export default router;
