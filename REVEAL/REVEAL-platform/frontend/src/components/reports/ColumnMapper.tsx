"use client";

import { useEffect, useState } from "react";
import Papa from "papaparse";
import type { AnalysisColumnMapping, ColumnDetectionResult, ColumnDetectionResult as Detection } from "@/types/analysis";
import { useTranslation } from "@/lib/i18n";

interface ColumnMapperProps {
  files: File[];
  siteType: "solar" | "wind";
  onMappingChange: (mappings: Record<string, AnalysisColumnMapping>) => void;
  onWorksheetChange?: (filename: string, worksheet: string) => void;
  detectedMappings?: Record<string, Detection>; // pre-filled from /detect-columns API
  worksheetLoadingFile?: string | null;
}

const SOLAR_ROLES = ["time", "power", "irradiance", "ambientTemperature", "moduleTemperature"] as const;
const WIND_ROLES = ["time", "power", "wind_speed", "wind_dir", "temperature"] as const;

function roleLabel(role: string) {
  switch (role) {
    case "time":
      return "Timestamp";
    case "power":
      return "Power channels";
    case "irradiance":
      return "Irradiance";
    case "temperature":
      return "Ambient temperature";
    case "ambientTemperature":
      return "Ambient temperature";
    case "moduleTemperature":
      return "Module temperature";
    case "wind_speed":
      return "Wind speed";
    case "wind_dir":
      return "Wind direction";
    default:
      return role.replace("_", " ");
  }
}

export function ColumnMapper({ files, siteType, onMappingChange, onWorksheetChange, detectedMappings, worksheetLoadingFile }: ColumnMapperProps) {
  const { t } = useTranslation();
  const [fileHeaders, setFileHeaders] = useState<Record<string, string[]>>({});
  const [mappings, setMappings] = useState<Record<string, AnalysisColumnMapping>>({});
  const [collapsedPowerLists, setCollapsedPowerLists] = useState<Record<string, boolean>>({});

  const roles = siteType === "solar" ? SOLAR_ROLES : WIND_ROLES;

  // Parse headers client-side with PapaParse (no upload needed just for column preview)
  useEffect(() => {
    const newHeaders: Record<string, string[]> = {};
    const promises = files.map(
      (file) =>
        new Promise<void>((resolve) => {
          const detectionHeaders = detectedMappings?.[file.name]?.columns;
          const isCsv = file.name.toLowerCase().endsWith(".csv") || file.type === "text/csv";

          if (!isCsv) {
            newHeaders[file.name] = detectionHeaders ?? [];
            resolve();
            return;
          }

          Papa.parse(file, {
            preview: 1,
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
              newHeaders[file.name] = results.meta.fields ?? detectionHeaders ?? [];
              resolve();
            },
            error: () => {
              newHeaders[file.name] = detectionHeaders ?? [];
              resolve();
            },
          });
        })
    );
    Promise.all(promises).then(() => setFileHeaders(newHeaders));
  }, [files, detectedMappings]);

  // Pre-fill from server detection
  useEffect(() => {
    if (!detectedMappings) return;
    const initial: Record<string, AnalysisColumnMapping> = {};
    for (const [fname, det] of Object.entries(detectedMappings)) {
      initial[fname] = {};
      if (det.selected_worksheet) {
        initial[fname].worksheet = det.selected_worksheet;
      }
      for (const role of roles) {
        const val = (det.mapping as Record<string, string | string[] | undefined>)[role];
        if (role === "power") {
          if (typeof val === "string") initial[fname].power = [val];
          else if (Array.isArray(val)) initial[fname].power = val;
        } else if (typeof val === "string") {
          initial[fname][role] = val;
        }
      }
    }
    setMappings(initial);
  }, [detectedMappings, roles]);

  function setRole(filename: string, role: string, col: string | string[]) {
    const next = { ...mappings, [filename]: { ...(mappings[filename] ?? {}), [role]: col } };
    setMappings(next);
    onMappingChange(next);
  }

  function getSelectValue(filename: string, role: (typeof roles)[number]) {
    const fileMapping = mappings[filename];
    if (role === "power") {
      const power = fileMapping?.power;
      if (Array.isArray(power)) return power;
      if (typeof power === "string") return [power];
      return [];
    }

    const value = fileMapping?.[role];
    return typeof value === "string" ? value : "";
  }

  if (files.length === 0) return null;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-200">{t("columns.title")}</h3>
        <p className="mt-1 text-xs text-slate-400">{t("columns.subtitle")}</p>
      </div>
      {files.map((file) => {
        const headers = fileHeaders[file.name] ?? [];
        const selectedPowerValue = getSelectValue(file.name, "power");
        const selectedPower = Array.isArray(selectedPowerValue) ? selectedPowerValue : [];
        const detection = detectedMappings?.[file.name];
        const worksheetOptions = detection?.worksheets ?? [];
        const selectedWorksheet = mappings[file.name]?.worksheet ?? detection?.selected_worksheet ?? worksheetOptions[0] ?? "";
        const worksheetBusy = worksheetLoadingFile === file.name;
        return (
          <div key={file.name} className="rounded-[24px] border border-white/10 bg-[rgba(3,16,26,0.84)] p-5 backdrop-blur-sm">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-100/70">Detected file</p>
                <h3 className="mt-2 font-dolfines text-xl font-semibold tracking-[0.04em] text-white">{file.name}</h3>
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-200">
                {headers.length} columns found
              </div>
            </div>

            {worksheetOptions.length > 1 ? (
              <div className="mb-4 rounded-[22px] border border-white/10 bg-white/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/55">Worksheet</p>
                    <p className="mt-1 text-xs text-slate-400">
                      Choose which Excel tab REVEAL should analyse for this file.
                    </p>
                  </div>
                  {worksheetBusy ? (
                    <span className="rounded-full border border-orange-400/30 bg-orange-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-orange-100">
                      Refreshing sheet
                    </span>
                  ) : null}
                </div>
                <select
                  value={selectedWorksheet}
                  onChange={(event) => {
                    const nextWorksheet = event.currentTarget.value;
                    setMappings((previous) => ({
                      ...previous,
                      [file.name]: {
                        ...(previous[file.name] ?? {}),
                        worksheet: nextWorksheet,
                      },
                    }));
                    onWorksheetChange?.(file.name, nextWorksheet);
                  }}
                  disabled={worksheetBusy}
                  className="mt-3 w-full rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.92)] px-4 py-3 text-sm font-medium text-white outline-none transition focus:border-orange-DEFAULT disabled:cursor-wait disabled:opacity-60"
                >
                  {worksheetOptions.map((worksheet) => (
                    <option key={worksheet} value={worksheet}>
                      {worksheet}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-2">
              {roles
                .filter((role) => role !== "power")
                .map((role) => (
                  <div key={role}>
                      <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-white/55">
                        {t(`columns.${role.replace("_", "")}`) === `columns.${role.replace("_", "")}`
                          ? roleLabel(role)
                          : t(`columns.${role.replace("_", "")}`)}
                      </label>
                    <select
                      value={getSelectValue(file.name, role)}
                      onChange={(e) => setRole(file.name, role, e.currentTarget.value)}
                      className="w-full rounded-2xl border border-white/12 bg-[rgba(5,20,32,0.92)] px-4 py-3 text-sm font-medium text-white outline-none transition focus:border-orange-DEFAULT"
                    >
                      <option value="">— none —</option>
                      {headers.map((h) => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                    {siteType === "solar" && role === "ambientTemperature" ? (
                      <p className="mt-2 text-xs leading-5 text-slate-400">
                        Supporting weather context. REVEAL uses ambient temperature as a fallback or reference when module temperature is unavailable.
                      </p>
                    ) : null}
                    {siteType === "solar" && role === "moduleTemperature" ? (
                      <p className="mt-2 text-xs leading-5 text-slate-400">
                        Preferred for PV PR correction versus STC. If provided, REVEAL applies the module temperature coefficient before calculating PR.
                      </p>
                    ) : null}
                  </div>
                ))}
            </div>

            <div className="mt-4 rounded-[22px] border border-white/10 bg-white/5 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/55">Power channels</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Select the inverter or equipment signals that should be summed into the site power total.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setRole(file.name, "power", headers)}
                    className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/10"
                  >
                    Select all
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole(file.name, "power", [])}
                    className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/10"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setCollapsedPowerLists((previous) => ({
                        ...previous,
                        [file.name]: !(previous[file.name] ?? false),
                      }))
                    }
                    className="rounded-full border border-white/12 bg-white/6 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100 transition hover:border-white/20 hover:bg-white/10"
                  >
                    {collapsedPowerLists[file.name] ? "Expand list" : "Collapse list"}
                  </button>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-[rgba(5,20,32,0.86)] px-4 py-3 text-sm text-slate-200">
                {selectedPower.length > 0
                  ? `${selectedPower.length} power channel${selectedPower.length === 1 ? "" : "s"} selected`
                  : "No power channels selected yet"}
              </div>

              {!collapsedPowerLists[file.name] ? (
                <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {headers.map((header) => {
                    const checked = selectedPower.includes(header);
                    return (
                      <button
                        key={header}
                        type="button"
                        onClick={() =>
                          setRole(file.name, "power", checked ? selectedPower.filter((item) => item !== header) : [...selectedPower, header])
                        }
                        className={`flex items-center gap-3 rounded-2xl border px-3 py-3 text-left text-sm transition ${
                          checked
                            ? "border-orange-DEFAULT bg-orange-DEFAULT/18 text-white"
                            : "border-white/10 bg-white/5 text-slate-200 hover:border-white/25 hover:bg-white/8"
                        }`}
                      >
                        <span
                          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] ${
                            checked ? "border-orange-100 bg-orange-DEFAULT text-white" : "border-white/30 text-transparent"
                          }`}
                        >
                          ✓
                        </span>
                        <span className="truncate">{header}</span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
