import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

export type SiteProfileDayType = "ouvre" | "weekend";

export interface SiteProfileWeight {
  month: number;
  day_type: SiteProfileDayType;
  hour: number;
  share: number;
}

export interface SiteLongTermProfileSummary {
  siteId: string;
  hasLongTermOutput: boolean;
  latestOutputFile: string | null;
  latestOutputGeneratedAt: string | null;
  averageAnnualEnergyMwh: number | null;
  profileWeights: SiteProfileWeight[];
  projectedYears: number;
}

type ParsedCsvRow = Record<string, string>;

function parseCsvLine(line: string) {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === "\"") {
      if (inQuotes && line[i + 1] === "\"") {
        current += "\"";
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === "," && !inQuotes) {
      values.push(current);
      current = "";
      continue;
    }
    current += char;
  }

  values.push(current);
  return values;
}

function parseCsv(content: string) {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.length > 0);

  if (lines.length === 0) return [] as ParsedCsvRow[];

  const headers = parseCsvLine(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return headers.reduce<ParsedCsvRow>((row, header, index) => {
      row[header] = values[index] ?? "";
      return row;
    }, {});
  });
}

function parseTimestamp(value: string) {
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function pickLatestFileName(fileNames: string[]) {
  return [...fileNames].sort((a, b) => b.localeCompare(a))[0] ?? null;
}

function buildProfileSummary(siteId: string, latestFile: string | null, csvContent: string | null): SiteLongTermProfileSummary {
  if (!latestFile || !csvContent) {
    return {
      siteId,
      hasLongTermOutput: false,
      latestOutputFile: null,
      latestOutputGeneratedAt: null,
      averageAnnualEnergyMwh: null,
      profileWeights: [],
      projectedYears: 0,
    };
  }

  const rows = parseCsv(csvContent);
  const projectedRows = rows.filter((row) => (row.mode || "").toLowerCase() === "projected");
  const usableRows = projectedRows.length > 0 ? projectedRows : rows;

  const annualTotals = new Map<number, number>();
  const shapeTotals = new Map<string, number>();
  let totalEnergy = 0;

  for (const row of usableRows) {
    const timestamp = parseTimestamp(row.timestamp_local || row.timestamp || "");
    const expectedEnergy = Number(row.expected_energy_mwh ?? "");
    if (!timestamp || !Number.isFinite(expectedEnergy) || expectedEnergy <= 0) continue;

    const year = timestamp.getFullYear();
    const month = timestamp.getMonth() + 1;
    const hour = timestamp.getHours();
    const dayType: SiteProfileDayType = timestamp.getDay() >= 6 ? "weekend" : "ouvre";
    const key = `${month}|${dayType}|${hour}`;

    annualTotals.set(year, (annualTotals.get(year) ?? 0) + expectedEnergy);
    shapeTotals.set(key, (shapeTotals.get(key) ?? 0) + expectedEnergy);
    totalEnergy += expectedEnergy;
  }

  const annualValues = [...annualTotals.values()];
  const averageAnnualEnergyMwh =
    annualValues.length > 0 ? annualValues.reduce((sum, value) => sum + value, 0) / annualValues.length : null;

  const profileWeights =
    totalEnergy > 0
      ? [...shapeTotals.entries()]
          .map(([key, value]) => {
            const [monthText, dayType, hourText] = key.split("|");
            return {
              month: Number(monthText),
              day_type: dayType as SiteProfileDayType,
              hour: Number(hourText),
              share: value / totalEnergy,
            };
          })
          .sort((a, b) => a.month - b.month || a.hour - b.hour || a.day_type.localeCompare(b.day_type))
      : [];

  return {
    siteId,
    hasLongTermOutput: true,
    latestOutputFile: latestFile,
    latestOutputGeneratedAt: null,
    averageAnnualEnergyMwh: averageAnnualEnergyMwh ? Math.round(averageAnnualEnergyMwh * 10) / 10 : null,
    profileWeights,
    projectedYears: annualTotals.size,
  };
}

export async function loadSiteLongTermProfile(siteId: string): Promise<SiteLongTermProfileSummary> {
  const baseDir = path.join(process.cwd(), "generated-long-term", siteId);
  const entries = await readdir(baseDir, { withFileTypes: true }).catch(() => []);
  const files = entries.filter((entry) => entry.isFile()).map((entry) => entry.name);
  const latestFile = pickLatestFileName(files);

  if (!latestFile) {
    return buildProfileSummary(siteId, null, null);
  }

  const latestPath = path.join(baseDir, latestFile);
  const csvContent = await readFile(latestPath, "utf-8").catch(() => null);
  return buildProfileSummary(siteId, latestFile, csvContent);
}
