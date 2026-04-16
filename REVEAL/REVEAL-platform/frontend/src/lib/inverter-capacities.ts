export interface InverterCapacityEntry {
  name: string;
  dcCapacityKwp: number;
}

const STORAGE_VERSION = 1;

function getStorageKey(siteId: string) {
  return `reveal-inverter-capacities-${STORAGE_VERSION}-${siteId}`;
}

export function loadInverterCapacities(siteId: string): InverterCapacityEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(getStorageKey(siteId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => ({
        name: String(item?.name ?? "").trim(),
        dcCapacityKwp: Number(item?.dcCapacityKwp ?? item?.capacityKw ?? 0),
      }))
      .filter((item) => item.name.length > 0 && Number.isFinite(item.dcCapacityKwp) && item.dcCapacityKwp > 0);
  } catch {
    return [];
  }
}

export function saveInverterCapacities(siteId: string, entries: InverterCapacityEntry[]) {
  if (typeof window === "undefined") return;
  const sanitized = entries
    .map((item) => ({
      name: String(item.name ?? "").trim(),
      dcCapacityKwp: Number(item.dcCapacityKwp ?? 0),
    }))
    .filter((item) => item.name.length > 0 && Number.isFinite(item.dcCapacityKwp) && item.dcCapacityKwp > 0);
  window.localStorage.setItem(getStorageKey(siteId), JSON.stringify(sanitized));
}
