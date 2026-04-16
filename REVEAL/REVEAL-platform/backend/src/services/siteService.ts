import fs from "fs";
import path from "path";
import crypto from "crypto";
import type { Site } from "../types/site";

// Seeded demo sites — mirrors platform_users.py
const DEMO_SITES: Site[] = [
  {
    id: "SOHMEX",
    display_name: "SOHMEX Solar Farm",
    country: "France",
    region: "Grand Est",
    cod: "01/06/2022",
    technology: "CdTe (First Solar Series 6)",
    site_type: "solar",
    status: "operational",
    lat: 48.8, lon: 6.1,
    cap_ac_kw: 5250, cap_dc_kwp: 4977,
    n_inverters: 21, inv_ac_kw: 250, inv_model: "Sungrow SG250HX",
    n_modules: 10815, module_wp: 460, module_brand: "First Solar",
    dc_ac_ratio: 0.948,
    design_pr: 0.80, operating_pr_target: 0.79,
    interval_min: 10, irr_threshold: 50, power_threshold: 5,
    plan_type: "unlimited",
  },
  {
    id: "VENTOUX_PV",
    display_name: "Ventoux PV",
    country: "France",
    region: "Provence-Alpes-Côte d'Azur",
    cod: "15/03/2021",
    technology: "Monocrystalline Si (Jinko Tiger)",
    site_type: "solar",
    status: "operational",
    lat: 44.17, lon: 5.28,
    cap_ac_kw: 3000, cap_dc_kwp: 3450,
    n_inverters: 12, inv_ac_kw: 250, inv_model: "Huawei SUN2000-250KTL",
    n_modules: 7500, module_wp: 460, module_brand: "Jinko",
    dc_ac_ratio: 1.15,
    design_pr: 0.81, operating_pr_target: 0.80,
    interval_min: 10, irr_threshold: 50, power_threshold: 5,
    plan_type: "unlimited",
  },
];

const CUSTOM_SITES_PATH = path.join(process.cwd(), "custom_sites.json");

function loadCustomSites(): Site[] {
  try {
    if (fs.existsSync(CUSTOM_SITES_PATH)) {
      return JSON.parse(fs.readFileSync(CUSTOM_SITES_PATH, "utf-8")) as Site[];
    }
  } catch {}
  return [];
}

function saveCustomSites(sites: Site[]) {
  fs.writeFileSync(CUSTOM_SITES_PATH, JSON.stringify(sites, null, 2));
}

export const siteService = {
  listForUser(_userId: string): Site[] {
    // In production: filter by owner_id / ACL. For now return all.
    return [...DEMO_SITES, ...loadCustomSites()];
  },

  getById(id: string): Site | undefined {
    return [...DEMO_SITES, ...loadCustomSites()].find((s) => s.id === id);
  },

  create(data: Omit<Site, "id">, userId: string): Site {
    const site: Site = {
      ...data,
      id: crypto.randomUUID(),
      owner_id: userId,
    };
    const custom = loadCustomSites();
    custom.push(site);
    saveCustomSites(custom);
    return site;
  },

  update(id: string, data: Partial<Site>): Site | null {
    const custom = loadCustomSites();
    const idx = custom.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    custom[idx] = { ...custom[idx], ...data };
    saveCustomSites(custom);
    return custom[idx];
  },

  delete(id: string): boolean {
    const custom = loadCustomSites();
    const filtered = custom.filter((s) => s.id !== id);
    if (filtered.length === custom.length) return false;
    saveCustomSites(filtered);
    return true;
  },
};
