"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import { BackLink } from "@/components/layout/BackLink";
import { getBessManufacturers, getBessModels, getBessSpec } from "@/lib/equipment-kb";
import { useTranslation } from "@/lib/i18n";
import {
  getCategoryKnowledge,
  getCompanyLogoUrl,
  knowledgeBase,
  type EquipmentCategory,
} from "@/lib/knowledge-base";

const categoryOrder: EquipmentCategory[] = ["inverter", "module", "turbine", "bess"];
const resourceSections = [
  { key: "equipment", label: "Equipment Intelligence" },
  { key: "long-term-distribution", label: "Long-Term Distribution" },
  { key: "optimize-to-p50", label: "Optimize to P50" },
  { key: "bess-framework", label: "BESS Space Calculator" },
  { key: "reporting-methodology", label: "Reporting Methodology" },
] as const;

type ResourceSectionKey = (typeof resourceSections)[number]["key"];

const longTermBlocks = [
  {
    title: "Purpose",
    body:
      "REVEAL will generate long-term hourly synthetic time series for solar and wind assets so users can test retrofit and optimization scenarios such as BESS integration, curtailment recovery, augmentation, and revenue modelling.",
  },
  {
    title: "Solar methodology",
    body:
      "For solar assets, REVEAL first checks that the site assumptions and reference-data settings are complete, then aligns uploaded measured data against a long-term reference source such as ERA5-Land. REVEAL calculates the measured specific yield from the uploaded operating period, shows the irradiance-fit correlation between site and reference data including R², and asks the user to confirm whether the measured period is representative before running the long-term projection.",
  },
  {
    title: "Irradiance-fit methodology",
    body:
      "For the irradiance-fit check, REVEAL only compares matched periods where valid site irradiance data exists. A matched day means at least 6 aligned hourly periods with valid values on the same day in both the site and ERA datasets. If site irradiance is missing for part of a day, the corresponding ERA reference hours are excluded from the regression as well. REVEAL then compares like-for-like irradiation totals over the valid matched hours so the fit is not biased by missing site data or by summing full-day ERA irradiation against partial measured coverage.",
  },
  {
    title: "Wind methodology",
    body:
      "For wind assets, REVEAL will correlate measured wind speed and net production against long-term reanalysis products such as ERA5 and MERRA. The normalized wind resource will then feed a cleaned turbine or farm-level production model to create a long-term hourly expected output series.",
  },
  {
    title: "Expected output",
    body:
      "The main output will be an hourly CSV suitable for engineering and commercial modelling. Each row may include timestamp, reference resource, corrected resource, expected gross output, expected net output, performance assumption, and confidence flags.",
  },
  {
    title: "Validation approach",
    body:
      "The user review step is part of the methodology. REVEAL reports measured AEP, projected AEP, measured specific yield, projected specific yield, and the irradiance-fit plot and R² over the matched comparison period. If the measured period is not representative, the user should upload more data or override the yield assumption with their own P50, P75, or P90 value before running the projection. The fit should be read as a confidence check on the matched-period quality rather than a blind acceptance step.",
  },
];

const reportingBlocks = [
  "REVEAL reporting is designed around transparent data ingestion, explicit column mapping, and traceable assumptions.",
  "Daily and comprehensive reports should use normalized SCADA inputs, documented site configuration, and reproducible analytics so that each output can be justified technically.",
  "This section is reserved for future documentation covering KPI definitions, alert logic, loss attribution, and report validation notes.",
];

const p50Blocks = [
  "This section will describe how REVEAL can move from observed operational behavior to an idealized long-term P50 production case once abnormal losses, outages, curtailment periods, and sensor bias have been identified and filtered.",
  "The intended workflow is to start from the operational extrapolation, then apply data-cleaning logic, reference-weather normalization, and plant-performance normalization so the resulting series represents an expected median technical case rather than the raw historical case.",
  "Future documentation here will explain which losses remain inside the model, which losses are excluded, how temperature and clipping are treated, and how the final P50 scenario differs from the directly extrapolated operational projection.",
];

function CompanyMark({ companyName }: { companyName: string }) {
  const brand =
    companyName.includes("Huawei")
      ? { label: "HUAWEI", className: "text-[#c7000b]" }
      : companyName.includes("First Solar")
        ? { label: "First Solar", className: "text-[#1a4f8b]" }
        : companyName.includes("LONGi")
          ? { label: "LONGi", className: "text-[#d93832]" }
          : { label: companyName.split(" ")[0], className: "text-slate-900" };

  return (
    <div className={`flex h-10 min-w-[40px] items-center justify-center px-2 text-center font-dolfines text-xs font-semibold tracking-[0.04em] ${brand.className}`}>
      {brand.label}
    </div>
  );
}

function severityClass(severity: string) {
  if (severity === "High") return "bg-[#8a1f1f]/80 text-red-100 border-red-200/25";
  if (severity === "Medium") return "bg-[#8f5b12]/70 text-amber-100 border-amber-200/25";
  return "bg-white/10 text-slate-100 border-white/15";
}

// Column definitions for the summary comparison table — indexed into model.specs[]
const SUMMARY_COLUMNS: Record<EquipmentCategory, { header: string; index: number }[]> = {
  inverter: [
    { header: "AC power", index: 0 },
    { header: "Max eff.", index: 1 },
    { header: "EU eff.", index: 2 },
    { header: "MPPTs", index: 3 },
    { header: "Max DC", index: 4 },
    { header: "IP rating", index: 5 },
  ],
  module: [
    { header: "Power", index: 0 },
    { header: "Efficiency", index: 1 },
    { header: "Technology", index: 2 },
    { header: "Bifaciality", index: 3 },
    { header: "Dimensions", index: 4 },
  ],
  turbine: [
    { header: "Rated", index: 0 },
    { header: "Rotor", index: 1 },
    { header: "Swept area", index: 2 },
    { header: "Hub height", index: 3 },
    { header: "IEC class", index: 4 },
  ],
  bess: [
    { header: "Power", index: 0 },
    { header: "Energy", index: 1 },
    { header: "Duration", index: 2 },
    { header: "Chemistry", index: 7 },
    { header: "Round-trip eff.", index: 8 },
    { header: "Capex indicator", index: 5 },
    { header: "Installed area", index: 6 },
    { header: "Deployment", index: 3 },
  ],
};

// Strip verbose suffixes from spec strings so they fit cleanly in table cells.
// The column header already provides the label context.
function cleanSpecValue(raw: string): string {
  return raw
    .replace(/ placeholder capex$/i, "")
    .replace(/ indicative installed area$/i, "")
    .replace(/ AC round-trip efficiency$/i, "")
    .replace(/ max efficiency$/i, "")
    .replace(/ EU efficiency$/i, "")
    .replace(/\bpower$/i, "")
    .replace(/ energy$/i, "")
    .replace(/ duration$/i, "")
    .replace(/ rated$/i, "")
    .replace(/ rotor$/i, "")
    .replace(/ swept area$/i, "")
    .replace(/ hub-height range$/i, "")
    .replace(/ max DC$/i, "")
    .replace(/ AC$/i, "")
    .trim();
}

function specToSortKey(raw: string): number | string {
  const cleaned = cleanSpecValue(raw);
  const m = cleaned.match(/^([\d,]+\.?\d*)/);
  if (m) return parseFloat(m[1].replace(/,/g, ""));
  return cleaned.toLowerCase();
}

type SortKey = "manufacturer" | "model" | number;

function EquipmentSection({ lang }: { lang: string }) {
  const [category, setCategory] = useState<EquipmentCategory>("inverter");
  const [view, setView] = useState<"summary" | "detail">("summary");
  const [sortKey, setSortKey] = useState<SortKey | null>("manufacturer");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const categoryKnowledge = getCategoryKnowledge(category);
  const [manufacturer, setManufacturer] = useState(categoryKnowledge.manufacturers[0]?.manufacturer ?? "");
  const [model, setModel] = useState(categoryKnowledge.manufacturers[0]?.models[0]?.model ?? "");

  const manufacturers = useMemo(() => getCategoryKnowledge(category).manufacturers, [category]);
  const selectedManufacturer = useMemo(
    () => manufacturers.find((item) => item.manufacturer === manufacturer) ?? manufacturers[0],
    [manufacturers, manufacturer]
  );

  const availableModels = useMemo(
    () => selectedManufacturer?.models.map((item) => item.model) ?? [],
    [selectedManufacturer]
  );

  const selectedModel = useMemo(
    () => selectedManufacturer?.models.find((item) => item.model === model) ?? selectedManufacturer?.models[0],
    [selectedManufacturer, model]
  );

  // Flat list of all models across all manufacturers for the comparison table
  const allRows = useMemo(
    () =>
      manufacturers.flatMap((mfr) =>
        mfr.models.map((mdl) => ({ manufacturer: mfr, modelEntry: mdl }))
      ),
    [manufacturers]
  );

  const sortedRows = useMemo(() => {
    if (sortKey === null) return allRows;
    return [...allRows].sort((a, b) => {
      let av: number | string;
      let bv: number | string;
      if (sortKey === "manufacturer") {
        av = a.manufacturer.company.name.toLowerCase();
        bv = b.manufacturer.company.name.toLowerCase();
      } else if (sortKey === "model") {
        av = a.modelEntry.model.toLowerCase();
        bv = b.modelEntry.model.toLowerCase();
      } else {
        av = specToSortKey(a.modelEntry.specs[sortKey] ?? "");
        bv = specToSortKey(b.modelEntry.specs[sortKey] ?? "");
      }
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [allRows, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function sortIndicator(key: SortKey) {
    if (sortKey !== key) return <span className="ml-1 opacity-25">↕</span>;
    return <span className="ml-1 text-orange-300">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  const totalModels = allRows.length;
  const summaryColumns = SUMMARY_COLUMNS[category];

  function openDetail(mfrName: string, mdlName: string) {
    setManufacturer(mfrName);
    setModel(mdlName);
    setView("detail");
  }

  const copy =
    lang === "fr"
      ? {
          chooseCategory: "Famille d’équipement",
          chooseManufacturer: "Fournisseur",
          chooseModel: "Modèle",
          companySummary: "Synthèse fournisseur",
          mainStat: "Repère industriel",
          monitoringFocus: "Points à surveiller dans REVEAL",
          issuesTitle: "Principaux points de vigilance",
          lookOutFor: "Signaux à surveiller",
          specs: "Repères techniques",
          empty: "Aucune fiche n’est encore disponible pour cette sélection.",
          backToOverview: "← Retour au tableau comparatif",
          deepDive: "Fiche détaillée →",
          overviewTitle: "Vue d’ensemble",
          overviewSub: "Comparez tous les modèles de cette catégorie, puis cliquez sur un produit pour accéder à sa fiche complète.",
        }
      : lang === "de"
        ? {
            chooseCategory: "Anlagenfamilie",
            chooseManufacturer: "Hersteller",
            chooseModel: "Modell",
            companySummary: "Unternehmensprofil",
            mainStat: "Industrieller Marker",
            monitoringFocus: "Was REVEAL zuerst überwachen sollte",
            issuesTitle: "Wesentliche Beobachtungspunkte",
            lookOutFor: "Zu beobachtende Signale",
            specs: "Technische Eckdaten",
            empty: "Für diese Auswahl ist noch keine Wissenskarte verfügbar.",
            backToOverview: "← Zurück zur Übersicht",
            deepDive: "Vollständiges Profil →",
            overviewTitle: "Übersicht",
            overviewSub: "Alle Modelle dieser Kategorie im Vergleich. Klicken Sie auf ein Produkt für das vollständige Profil.",
          }
        : {
            chooseCategory: "Equipment family",
            chooseManufacturer: "Manufacturer",
            chooseModel: "Model",
            companySummary: "Company Summary",
            mainStat: "Industry marker",
            monitoringFocus: "What to monitor first in REVEAL",
            issuesTitle: "Main Watchouts",
            lookOutFor: "Signals to watch",
            specs: "Technical markers",
            empty: "No knowledge card is available yet for this selection.",
            backToOverview: "← Back to overview",
            deepDive: "Full profile →",
            overviewTitle: "Overview",
            overviewSub: "Compare all products in this category, then click any row to open the full manufacturer and model profile.",
          };

  const selectClass =
    "h-12 w-full rounded-2xl border border-white/15 bg-[rgba(4,18,28,0.78)] px-4 text-sm font-semibold text-white outline-none transition focus:border-orange-DEFAULT focus:ring-2 focus:ring-orange-DEFAULT/30";

  // ── Category selector — always visible ──────────────────────────────────────
  const categorySelector = (
    <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.68)] p-5 backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {categoryOrder.map((item) => {
            const entry = knowledgeBase.find((v) => v.key === item);
            const label = lang === "fr" ? entry?.label.fr : entry?.label.en;
            const isActive = category === item;
            return (
              <button
                key={item}
                onClick={() => {
                  const nextKnowledge = getCategoryKnowledge(item);
                  setCategory(item);
                  setManufacturer(nextKnowledge.manufacturers[0]?.manufacturer ?? "");
                  setModel(nextKnowledge.manufacturers[0]?.models[0]?.model ?? "");
                  setView("summary");
                  setSortKey("manufacturer");
                  setSortDir("asc");
                }}
                className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
                  isActive
                    ? "border-orange-DEFAULT/50 bg-orange-DEFAULT/20 text-orange-100"
                    : "border-white/12 bg-white/5 text-slate-300 hover:border-white/24 hover:text-white"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
        {view === "detail" && (
          <button
            onClick={() => setView("summary")}
            className="text-sm font-medium text-slate-300 hover:text-white transition"
          >
            {copy.backToOverview}
          </button>
        )}
      </div>
    </div>
  );

  // ── Summary / comparison view ────────────────────────────────────────────────
  if (view === "summary") {
    return (
      <div className="space-y-5">
        {categorySelector}

        {/* Category header */}
        <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">
                {lang === "fr" ? categoryKnowledge.label.fr : categoryKnowledge.label.en}
                {" "}— {copy.overviewTitle}
              </p>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-200/82">
                {lang === "fr" ? categoryKnowledge.description.fr : categoryKnowledge.description.en}
              </p>
              <p className="mt-3 text-xs text-slate-400">{copy.overviewSub}</p>
            </div>
            <div className="flex gap-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center">
                <p className="text-xl font-bold text-white">{manufacturers.length}</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-400">Manufacturers</p>
              </div>
              <div className="rounded-2xl border border-orange-DEFAULT/25 bg-orange-DEFAULT/8 px-4 py-3 text-center">
                <p className="text-xl font-bold text-white">{totalModels}</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-orange-300">Models</p>
              </div>
            </div>
          </div>
        </div>

        {/* Comparison table */}
        <div className="overflow-hidden rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/4">
                  {(["manufacturer", "model"] as const).map((key) => (
                    <th key={key} className="px-5 py-3.5 text-left">
                      <button
                        onClick={() => handleSort(key)}
                        className="flex items-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400 hover:text-white transition whitespace-nowrap"
                      >
                        {key === "manufacturer" ? "Manufacturer" : "Model"}
                        {sortIndicator(key)}
                      </button>
                    </th>
                  ))}
                  {summaryColumns.map((col) => (
                    <th key={col.header} className="px-5 py-3.5 text-left">
                      <button
                        onClick={() => handleSort(col.index)}
                        className="flex items-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400 hover:text-white transition whitespace-nowrap"
                      >
                        {col.header}
                        {sortIndicator(col.index)}
                      </button>
                    </th>
                  ))}
                  <th className="px-5 py-3.5" />
                </tr>
              </thead>
              <tbody>
                {sortedRows.map(({ manufacturer: mfr, modelEntry }, rowIdx) => (
                  <tr
                    key={`${mfr.manufacturer}-${modelEntry.model}`}
                    className={`border-b border-white/6 transition hover:bg-white/5 cursor-pointer ${rowIdx % 2 === 0 ? "" : "bg-white/[0.015]"}`}
                    onClick={() => openDetail(mfr.manufacturer, modelEntry.model)}
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="h-2 w-2 flex-shrink-0 rounded-full bg-white/40" />
                        <span className="font-semibold text-white">{mfr.company.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-200 whitespace-nowrap">{modelEntry.model}</td>
                    {summaryColumns.map((col) => (
                      <td key={col.header} className="px-5 py-3 text-slate-300 whitespace-nowrap">
                        {modelEntry.specs[col.index] != null ? cleanSpecValue(modelEntry.specs[col.index]) : "—"}
                      </td>
                    ))}
                    <td className="px-5 py-3 text-right">
                      <span className="rounded-lg border border-white/12 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition">
                        {copy.deepDive}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Manufacturer cards grid */}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {manufacturers.map((mfr) => (
            <button
              key={mfr.manufacturer}
              onClick={() => openDetail(mfr.manufacturer, mfr.models[0]?.model ?? "")}
              className="rounded-[24px] border border-white/10 bg-[rgba(4,18,28,0.68)] p-5 text-left transition hover:border-white/22 hover:bg-[rgba(4,18,28,0.85)]"
            >
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white/95`}>
                  {["Huawei FusionSolar", "First Solar", "LONGi Solar", "LONGi"].includes(mfr.company.name) ? (
                    <CompanyMark companyName={mfr.company.name} />
                  ) : (
                    <Image
                      src={getCompanyLogoUrl(mfr.company)}
                      alt={`${mfr.company.name} logo`}
                      width={28}
                      height={28}
                      unoptimized
                      className="h-7 w-7 object-contain"
                    />
                  )}
                </div>
                <div>
                  <p className="font-dolfines font-semibold tracking-[0.04em] text-white">{mfr.company.name}</p>
                  <p className="text-[11px] text-slate-400">{mfr.models.length} model{mfr.models.length !== 1 ? "s" : ""} · {mfr.company.headquarters}</p>
                </div>
              </div>
              <p className="mt-3 line-clamp-2 text-xs leading-5 text-slate-300/80">{mfr.company.overview}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {mfr.models.slice(0, 3).map((mdl) => (
                  <span key={mdl.model} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-300">
                    {mdl.model}
                  </span>
                ))}
                {mfr.models.length > 3 && (
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">
                    +{mfr.models.length - 3} more
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ── Detail view ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {categorySelector}

      <section className="grid gap-4 rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.68)] p-5 backdrop-blur-sm lg:grid-cols-2">
        <label className="space-y-2">
          <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">{copy.chooseManufacturer}</span>
          <select
            value={selectedManufacturer?.manufacturer ?? ""}
            className={selectClass}
            onChange={(event) => {
              const nextManufacturer = event.target.value;
              const nextKnowledge = manufacturers.find((item) => item.manufacturer === nextManufacturer);
              setManufacturer(nextManufacturer);
              setModel(nextKnowledge?.models[0]?.model ?? "");
            }}
          >
            {manufacturers.map((item) => (
              <option key={item.manufacturer} value={item.manufacturer}>
                {item.company.name}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">{copy.chooseModel}</span>
          <select value={selectedModel?.model ?? ""} className={selectClass} onChange={(event) => setModel(event.target.value)}>
            {availableModels.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </section>

      {!selectedManufacturer || !selectedModel ? (
        <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.68)] p-8 text-sm text-slate-200">{copy.empty}</div>
      ) : (
        <section className="grid gap-6 xl:grid-cols-[1.05fr_1.4fr]">
          <aside className="space-y-5 rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
            <div className={`rounded-[24px] bg-gradient-to-br ${selectedManufacturer.company.accent} p-[1px] shadow-[0_16px_36px_rgba(0,0,0,0.22)]`}>
              <div className="rounded-[23px] border border-white/6 bg-[rgba(3,18,28,0.92)] px-5 pb-6 pt-5">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl bg-white/95 shadow-[0_10px_30px_rgba(0,0,0,0.15)]">
                    {["Huawei FusionSolar", "First Solar", "LONGi Solar", "LONGi"].includes(selectedManufacturer.company.name) ? (
                      <CompanyMark companyName={selectedManufacturer.company.name} />
                    ) : (
                      <Image
                        src={getCompanyLogoUrl(selectedManufacturer.company)}
                        alt={`${selectedManufacturer.company.name} logo`}
                        width={40}
                        height={40}
                        unoptimized
                        className="h-10 w-10 object-contain"
                      />
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">{selectedManufacturer.company.name}</p>
                    <p className="text-xs uppercase tracking-[0.28em] text-white/60">{copy.companySummary}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-200/88">{selectedManufacturer.company.overview}</p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-white/50">{copy.mainStat}</p>
                <p className="mt-2 text-sm font-semibold text-white">{selectedManufacturer.company.statValue}</p>
                <p className="mt-1 text-xs text-slate-300">{selectedManufacturer.company.statLabel}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-white/50">{lang === "fr" ? "Création" : lang === "de" ? "Gründung" : "Founded"}</p>
                <p className="mt-2 text-sm font-semibold text-white">{selectedManufacturer.company.founded}</p>
                <p className="mt-1 text-xs text-slate-300">{selectedManufacturer.company.headquarters}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">{copy.specs}</p>
              <div className="mt-3 grid gap-x-4 gap-y-1 sm:grid-cols-2">
                {selectedModel.specs.map((item) => (
                  <div key={item} className="border-b border-white/8 py-2 text-sm text-slate-100 last:border-b-0">
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">{copy.monitoringFocus}</p>
              <div className="mt-3 space-y-2">
                {selectedModel.monitoringFocus.map((item) => (
                  <div key={item} className="rounded-xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm text-slate-200">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </aside>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
              <p className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">{copy.issuesTitle}</p>
              <p className="mt-2 text-sm text-slate-300">{lang === "fr" ? categoryKnowledge.description.fr : categoryKnowledge.description.en}</p>
            </div>

            {selectedModel.issues.map((issue) => (
              <article key={issue.title} className="rounded-[24px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">{issue.title}</h2>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${severityClass(issue.severity)}`}>
                    {issue.severity}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-200/88">{issue.summary}</p>

                <div className="mt-5 rounded-2xl border border-white/8 bg-white/5 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/58">{copy.lookOutFor}</p>
                  <div className="mt-3 space-y-2">
                    {issue.lookOutFor.map((signal) => (
                      <div key={signal} className="rounded-xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm text-slate-200">
                        {signal}
                      </div>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function LongTermDistributionSection() {
  const flow = [
    { label: "Upload actual data", accent: "from-sky-400/90 to-sky-600/70" },
    { label: "Site assumptions and reference weather", accent: "from-emerald-400/90 to-emerald-600/70" },
    { label: "Screen bad data", accent: "from-amber-300/95 to-amber-500/70" },
    { label: "Review fit and yield", accent: "from-teal-300/95 to-teal-500/70" },
    { label: "Confirm yield and download the data", accent: "from-violet-300/95 to-violet-500/70" },
  ];

  return (
    <div className="space-y-5">
      <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
        <p className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">Long-Term Distribution</p>
        <div className="mt-3 overflow-x-auto">
          <p className="min-w-max whitespace-nowrap text-sm leading-7 text-slate-200/88">
          This section describes the methodology REVEAL will use to create long-term hourly synthetic data sets for solar and wind sites.
          The purpose is to generate modelling-grade time series that can support BESS retrofit studies, curtailment recovery analysis,
          long-term performance benchmarking, and future hybrid optimization workflows.
          </p>
        </div>
      </div>

      <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">Workflow overview</p>
            <p className="mt-2 text-sm leading-7 text-slate-200/84">
              REVEAL should move from measured operational data to a long-term synthetic time series through an explicit five-step workflow with a user confirmation gate before projection.
            </p>
          </div>
          <div className="rounded-full border border-white/10 bg-white/6 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">
            Engineering-grade logic
          </div>
        </div>
        <div className="mt-6 grid gap-4 xl:grid-cols-5">
          {flow.map((item, index) => (
            <div key={item.label} className="relative rounded-[24px] border border-white/10 bg-white/5 p-5">
              <div className={`h-2 w-full rounded-full bg-gradient-to-r ${item.accent}`} />
              <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-white/45">{`Step ${index + 1}`}</p>
              <p className="mt-2 font-dolfines text-lg font-semibold tracking-[0.04em] text-white">{item.label}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-3">
          {[
            "1. Upload the measured SCADA data, let REVEAL analyse the structure, and confirm or adjust the detected columns.",
            "2. Confirm the site assumptions, timezone, output horizon, and reference-weather settings, then fetch the ERA reference weather.",
            "3. Run the bad-data screen so REVEAL can remove frozen power and irradiance periods before any fit review or projection logic is applied.",
            "4. Review the cleaned irradiation fit, regression, R², seasonality, measured specific yield, and matched-day counts to decide whether the period is representative.",
            "5. Confirm the specific-yield basis and only then generate and download the long-term modelling output. If the checks fail, the user should upload better data or override the yield with a manual P50, P75, or P90 value.",
          ].map((item) => (
            <div key={item} className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3 text-sm leading-7 text-slate-100">
              {item}
            </div>
          ))}
        </div>
        <div className="mt-6 rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-dolfines text-lg font-semibold tracking-[0.04em] text-white">Visual workflow</p>
              <p className="mt-1 text-sm leading-6 text-slate-300/82">
                A branching view of how REVEAL moves from site setup to a reviewed long-term projection.
              </p>
            </div>
            <div className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">
              Decision paths included
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <div className="grid gap-4 xl:grid-cols-3">
              <div className="rounded-[22px] border border-sky-300/20 bg-sky-400/10 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-100/75">Step 1</p>
                <p className="mt-2 font-dolfines text-lg font-semibold tracking-[0.04em] text-white">Upload actual data</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/84">
                  Upload the measured workbook, let REVEAL analyse the structure, and confirm the detected timestamps, power, irradiance, and temperature mappings.
                </p>
              </div>

              <div className="rounded-[22px] border border-emerald-300/20 bg-emerald-400/10 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-100/75">Step 2</p>
                <p className="mt-2 font-dolfines text-lg font-semibold tracking-[0.04em] text-white">Set assumptions and fetch weather</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/84">
                  Confirm the plant context, timezone, output horizon, and reference-weather settings, then fetch the ERA reference weather for the site.
                </p>
              </div>

              <div className="rounded-[22px] border border-amber-300/20 bg-amber-400/10 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-100/75">Step 3</p>
                <p className="mt-2 font-dolfines text-lg font-semibold tracking-[0.04em] text-white">Screen bad data</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/84">
                  REVEAL highlights frozen power and irradiance windows, builds the daily heat map, and excludes those periods before calibration.
                </p>
              </div>
            </div>

            <div className="flex justify-center text-2xl text-white/35">
              <span>↓</span>
            </div>

            <div className="rounded-[24px] border border-teal-300/20 bg-teal-400/10 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-teal-100/75">Step 4</p>
                  <p className="mt-2 font-dolfines text-lg font-semibold tracking-[0.04em] text-white">Review fit and yield</p>
                  <p className="mt-2 text-sm leading-6 text-slate-200/84">
                    The user reviews the cleaned irradiation fit, regression, R², specific yield, seasonality, and matched-day diagnostics before projection unlocks.
                  </p>
                </div>
                <div className="rounded-full border border-white/10 bg-white/6 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/80">
                  Review gate
                </div>
              </div>

              <div className="mt-5 grid gap-4 xl:grid-cols-3">
                <div className="rounded-[20px] border border-emerald-300/20 bg-emerald-400/10 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-100/75">Path A</p>
                  <p className="mt-2 font-dolfines text-base font-semibold tracking-[0.04em] text-white">Fit is acceptable</p>
                  <p className="mt-2 text-sm leading-6 text-slate-200/84">
                    The R², matched-day counts, and measured specific yield look representative of the site. REVEAL can use the measured calibration directly.
                  </p>
                  <div className="mt-4 flex items-center gap-2 text-sm font-medium text-emerald-100">
                    <span className="text-lg">→</span>
                    Proceed to long-term projection
                  </div>
                </div>

                <div className="rounded-[20px] border border-rose-300/20 bg-rose-400/10 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-100/75">Path B</p>
                  <p className="mt-2 font-dolfines text-base font-semibold tracking-[0.04em] text-white">Specific yield looks too low</p>
                  <p className="mt-2 text-sm leading-6 text-slate-200/84">
                    This can indicate outages, curtailment, bad coverage, or a non-representative period. The user should review site history or override the yield before projecting.
                  </p>
                  <div className="mt-4 space-y-2 text-sm text-rose-100">
                    <p>→ Upload a better or longer measured period</p>
                    <p>→ Or override the yield with a manual P50, P75, or P90 value</p>
                  </div>
                </div>

                <div className="rounded-[20px] border border-cyan-300/20 bg-cyan-400/10 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-100/75">Path C</p>
                  <p className="mt-2 font-dolfines text-base font-semibold tracking-[0.04em] text-white">Irradiance fit is weak</p>
                  <p className="mt-2 text-sm leading-6 text-slate-200/84">
                    A weak matched-day correlation suggests sensor issues, poor mapping, timezone problems, or a period that does not reflect the site properly.
                  </p>
                  <div className="mt-4 space-y-2 text-sm text-cyan-100">
                    <p>→ Re-check the irradiance column and timestamps</p>
                    <p>→ Or upload a cleaner overlap period before projection</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1fr_auto_1fr]">
              <div className="rounded-[20px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/55">Iteration loop</p>
                <p className="mt-2 font-dolfines text-base font-semibold tracking-[0.04em] text-white">If checks fail</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/84">
                  Go back to the measured data step, upload more representative data, or adjust the manual yield basis before trying again.
                </p>
              </div>

              <div className="hidden items-center justify-center xl:flex">
                <div className="flex h-full items-center text-2xl text-white/35">
                  <span>↺</span>
                </div>
              </div>

              <div className="rounded-[20px] border border-violet-300/20 bg-violet-400/10 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-100/75">Step 5</p>
                <p className="mt-2 font-dolfines text-base font-semibold tracking-[0.04em] text-white">Confirm yield and download the data</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/84">
                  Once the user confirms the specific-yield basis, REVEAL generates the final long-term output file and the user downloads the modelling-ready hourly data.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
          <p className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">Visual target for the model output</p>
            <div className="mt-5 rounded-[22px] border border-white/8 bg-white/5 p-5">
              <div className="rounded-[18px] border border-white/6 bg-[linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01))] p-4">
                <div className="flex h-40 items-end gap-2">
                  {[68, 72, 74, 76, 78, 79, 81, 82, 83, 84, 84, 85, 86, 87, 88, 88, 89, 90, 90, 91].map((height, index) => {
                    const isActual = index < 2;
                    return (
                      <div key={index} className="flex h-full flex-1 flex-col justify-end gap-2">
                        <div
                          className={`w-full rounded-t-[14px] ${
                            isActual
                              ? "bg-[linear-gradient(180deg,#fbbf24,#f59e0b)] shadow-[0_10px_26px_rgba(245,158,11,0.35)]"
                              : "bg-[linear-gradient(180deg,#60a5fa,#2563eb)] shadow-[0_10px_26px_rgba(37,99,235,0.28)]"
                          }`}
                          style={{ height: `${height}%`, minHeight: "22px" }}
                        />
                        <span className="text-center text-[11px] font-medium text-slate-400">{`Y${index + 1}`}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="mt-5 flex items-center gap-3 text-xs text-slate-300/82">
                <span className="inline-flex h-3 w-3 rounded-full bg-amber-300" />
                Years 1-2 measured operational data
              <span className="inline-flex h-3 w-3 rounded-full bg-sky-400" />
              Additional projected years generated after the measured period
              <span className="inline-flex h-3 w-3 rounded-full bg-emerald-300" />
              Reference source: ERA5-Land hourly irradiance
            </div>
            <p className="mt-4 text-xs leading-6 text-slate-300/88">
              Concept view: the application shows the measured operating years first, then appends an additional projected sequence generated from corrected reference irradiance and site-normalized performance behavior.
            </p>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
          <p className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">Decision-use outputs</p>
          <div className="mt-5 space-y-3">
            {[
              "BESS retrofit screening",
              "Curtailment recovery studies",
              "Augmentation and repowering review",
              "Long-term production benchmarking",
              "Revenue and dispatch modelling",
            ].map((item) => (
              <div key={item} className="rounded-2xl border border-white/8 bg-[rgba(255,255,255,0.04)] px-4 py-3 text-sm font-medium text-slate-100">
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {longTermBlocks.map((block) => (
          <article key={block.title} className="rounded-[24px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
            <h2 className="font-dolfines text-xl font-semibold tracking-[0.04em] text-white">{block.title}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-200/88">{block.body}</p>
          </article>
        ))}
      </div>

      <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
        <p className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">Planned hourly CSV output</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[
            "timestamp",
            "site_id",
            "asset_type",
            "reference_source",
            "corrected_resource_value",
            "expected_gross_output",
            "expected_net_output",
            "expected_pr_or_efficiency",
            "confidence_class",
          ].map((item) => (
            <div key={item} className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-sm font-medium text-slate-100">
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SimpleTextSection({
  title,
  subtitle,
  points,
}: {
  title: string;
  subtitle: string;
  points: string[];
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
        <p className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">{title}</p>
        <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-200/88">{subtitle}</p>
      </div>
      <div className="space-y-3">
        {points.map((point, index) => (
          <div key={index} className="rounded-[22px] border border-white/10 bg-[rgba(4,18,28,0.72)] px-5 py-4 text-sm leading-7 text-slate-200/88 backdrop-blur-sm">
            {point}
          </div>
        ))}
      </div>
    </div>
  );
}

function BessFrameworkSection() {
  type CatalogBessEntry = {
    manufacturer: string;
    model: string;
    spec: NonNullable<ReturnType<typeof getBessSpec>>;
  };

  const allBessEntries = useMemo(
    () =>
      getBessManufacturers().flatMap((manufacturer) =>
        getBessModels(manufacturer).reduce<CatalogBessEntry[]>((entries, model) => {
          const spec = getBessSpec(manufacturer, model);
          if (spec) {
            entries.push({
              manufacturer,
              model,
              spec,
            });
          }
          return entries;
        }, [])
      ),
    []
  );

  const technologyOptions = useMemo(() => {
    const chemistries = Array.from(new Set(allBessEntries.map((entry) => entry.spec.chemistry).filter(Boolean))).sort();
    return ["All utility-scale BESS", ...chemistries];
  }, [allBessEntries]);

  const [selectedTechnology, setSelectedTechnology] = useState<string>("All utility-scale BESS");
  const [selectedModelKey, setSelectedModelKey] = useState<string>("auto");
  const [powerMw, setPowerMw] = useState<string>("5");
  const [durationHours, setDurationHours] = useState<string>("2");

  const selectClass =
    "h-12 w-full rounded-2xl border border-white/15 bg-[rgba(4,18,28,0.78)] px-4 text-sm font-semibold text-white outline-none transition focus:border-orange-DEFAULT focus:ring-2 focus:ring-orange-DEFAULT/30";

  const targetPowerMw = Math.max(Number(powerMw) || 0, 0);
  const targetDurationHours = Math.max(Number(durationHours) || 0, 0);
  const targetEnergyMwh = targetPowerMw * targetDurationHours;

  const filteredEntries = useMemo(() => {
    if (selectedTechnology === "All utility-scale BESS") return allBessEntries;
    return allBessEntries.filter((entry) => entry.spec.chemistry === selectedTechnology);
  }, [allBessEntries, selectedTechnology]);

  const modelOptions = useMemo(
    () => [
      { key: "auto", label: "Auto-select from current filter" },
      ...filteredEntries.map((entry) => ({
        key: `${entry.manufacturer}::${entry.model}`,
        label: `${entry.manufacturer} ${entry.model}`,
      })),
    ],
    [filteredEntries]
  );

  const selectedModelEntry = useMemo(() => {
    if (selectedModelKey === "auto") return null;
    return filteredEntries.find((entry) => `${entry.manufacturer}::${entry.model}` === selectedModelKey) ?? null;
  }, [filteredEntries, selectedModelKey]);

  const calculator = useMemo(() => {
    if (!filteredEntries.length || targetPowerMw <= 0 || targetDurationHours <= 0 || targetEnergyMwh <= 0) return null;

    const basisEntries = selectedModelEntry ? [selectedModelEntry] : filteredEntries;

    const energyDensityValues = basisEntries
      .filter((entry) => entry.spec.area_with_access_m2 != null && entry.spec.energy_mwh > 0)
      .map((entry) => (entry.spec.area_with_access_m2 as number) / entry.spec.energy_mwh);

    const footprintDensityValues = basisEntries
      .filter((entry) => entry.spec.footprint_m2 != null && entry.spec.energy_mwh > 0)
      .map((entry) => (entry.spec.footprint_m2 as number) / entry.spec.energy_mwh);

    const capexValues = basisEntries
      .map((entry) => entry.spec.cost_eur_kwh)
      .filter((value): value is number => value != null && value > 0);

    if (!energyDensityValues.length || !footprintDensityValues.length) return null;

    const avgAreaPerMwh = energyDensityValues.reduce((sum, value) => sum + value, 0) / energyDensityValues.length;
    const minAreaPerMwh = Math.min(...energyDensityValues);
    const maxAreaPerMwh = Math.max(...energyDensityValues);
    const avgFootprintPerMwh = footprintDensityValues.reduce((sum, value) => sum + value, 0) / footprintDensityValues.length;
    const avgCapexEurKwh = capexValues.length ? capexValues.reduce((sum, value) => sum + value, 0) / capexValues.length : 200;

    const referenceEntry = [...basisEntries].sort((a, b) => {
      const scoreA =
        Math.abs(a.spec.duration_hours - targetDurationHours) * 3 +
        Math.abs(a.spec.energy_mwh - targetEnergyMwh) / Math.max(targetEnergyMwh, 1) +
        Math.abs(a.spec.power_mw - targetPowerMw) / Math.max(targetPowerMw, 1);
      const scoreB =
        Math.abs(b.spec.duration_hours - targetDurationHours) * 3 +
        Math.abs(b.spec.energy_mwh - targetEnergyMwh) / Math.max(targetEnergyMwh, 1) +
        Math.abs(b.spec.power_mw - targetPowerMw) / Math.max(targetPowerMw, 1);
      return scoreA - scoreB;
    })[0];

    return {
      targetEnergyMwh,
      equipmentFootprintM2: targetEnergyMwh * avgFootprintPerMwh,
      estimatedAreaM2: targetEnergyMwh * avgAreaPerMwh,
      lowAreaM2: targetEnergyMwh * minAreaPerMwh,
      highAreaM2: targetEnergyMwh * maxAreaPerMwh,
      capexEur: targetEnergyMwh * 1000 * avgCapexEurKwh,
      referenceEntry,
      basisCount: basisEntries.length,
    };
  }, [filteredEntries, selectedModelEntry, targetDurationHours, targetEnergyMwh, targetPowerMw]);

  return (
    <div className="space-y-5">
      <div className="rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-6 backdrop-blur-sm">
        <p className="font-dolfines text-2xl font-semibold tracking-[0.05em] text-white">BESS Space Calculator</p>
      </div>

      <section className="rounded-[28px] border border-orange-DEFAULT/20 bg-[linear-gradient(180deg,rgba(243,146,0,0.08),rgba(4,18,28,0.78))] p-6 backdrop-blur-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-dolfines text-xl font-semibold tracking-[0.05em] text-white">BESS space calculator</p>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-200/82">
                Choose a target power, duration, battery technology, and if needed an exact reference model. REVEAL shows both the equipment footprint based on product geometry and an indicative installed area for early-stage site screening.
              </p>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-orange-100/72">
                Data source: Equipment intelligence section
              </p>
            </div>
            <div className="rounded-full border border-orange-DEFAULT/25 bg-orange-DEFAULT/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-orange-100">
              Indicative result
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-2">
              <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">Power</span>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={powerMw}
                  onChange={(event) => setPowerMw(event.target.value)}
                  className={`${selectClass} pr-16`}
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-xs font-semibold uppercase tracking-[0.18em] text-white/55">MW</span>
              </div>
            </label>

            <label className="space-y-2">
              <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">Duration</span>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  value={durationHours}
                  onChange={(event) => setDurationHours(event.target.value)}
                  className={`${selectClass} pr-16`}
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-xs font-semibold uppercase tracking-[0.18em] text-white/55">h</span>
              </div>
            </label>

            <label className="space-y-2">
              <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">Technology</span>
              <select
                value={selectedTechnology}
                onChange={(event) => {
                  setSelectedTechnology(event.target.value);
                  setSelectedModelKey("auto");
                }}
                className={selectClass}
              >
                {technologyOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em] text-white">Specific model</span>
              <select value={selectedModelKey} onChange={(event) => setSelectedModelKey(event.target.value)} className={selectClass}>
                {modelOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {calculator ? (
            <div className="mt-6 space-y-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/50">Energy size</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{calculator.targetEnergyMwh.toFixed(2)} MWh</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/50">Equipment footprint</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{Math.round(calculator.equipmentFootprintM2).toLocaleString()} m2</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/50">Indicative area</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{Math.round(calculator.estimatedAreaM2).toLocaleString()} m2</p>
                  <p className="mt-1 text-xs text-slate-300">{(calculator.estimatedAreaM2 / 10000).toFixed(2)} ha</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/50">Typical range</p>
                  <p className="mt-2 text-2xl font-semibold text-white">
                    {Math.round(calculator.lowAreaM2).toLocaleString()}-{Math.round(calculator.highAreaM2).toLocaleString()} m2
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/50">Placeholder capex</p>
                  <p className="mt-2 text-2xl font-semibold text-white">EUR {Math.round(calculator.capexEur).toLocaleString()}</p>
                </div>
              </div>

              <div className="rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/58">Reference basis</p>
                <p className="mt-2 text-sm leading-6 text-slate-200/88">
                  The estimate is derived from REVEAL&apos;s current catalog entries for <span className="font-semibold text-white">{selectedTechnology}</span>
                  {selectedModelEntry ? (
                    <>
                      {" "}using the exact selected model basis:
                    </>
                  ) : (
                    <>
                      {" "}and is anchored to the closest available reference product:
                    </>
                  )}
                  {" "}
                  <span className="font-semibold text-white">
                    {calculator.referenceEntry.manufacturer} {calculator.referenceEntry.model}
                  </span>.
                </p>
                {!selectedModelEntry ? (
                  <p className="mt-2 text-xs leading-6 text-slate-300/82">
                    Current estimate blends {calculator.basisCount} catalog entries in the active technology filter.
                  </p>
                ) : null}
                <p className="mt-2 text-xs leading-6 text-slate-300/82">
                  Equipment footprint is based on the product enclosure geometry or official container form factor. Indicative installed area remains a planning screen for early-stage feasibility and depends on access roads, fire spacing, PCS/transformer arrangement, and local permitting constraints.
                </p>
              </div>
            </div>
          ) : (
            <div className="mt-6 rounded-[22px] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4 text-sm text-slate-200/84">
              Enter a valid power and duration to calculate an indicative installed area.
            </div>
          )}
      </section>
    </div>
  );
}

export default function KnowledgeBasePage() {
  const { lang } = useTranslation();
  const [activeSection, setActiveSection] = useState<ResourceSectionKey>("equipment");

  const copy =
    lang === "fr"
      ? {
          title: "Base de ressources",
          subtitle:
            "Une bibliothèque REVEAL structurée pour centraliser les références techniques, les profils fournisseurs, les méthodologies analytiques et les futurs cadres BESS.",
          powered: "Bibliothèque REVEAL d'8p2 Advisory",
          back: "Retour au tableau de bord",
        }
      : lang === "de"
        ? {
            title: "Ressourcendatenbank",
            subtitle:
              "Eine strukturierte REVEAL-Bibliothek für technische Referenzen, Herstellerprofile, analytische Methoden und künftige BESS-Rahmenwerke.",
            powered: "8p2 Advisory REVEAL Bibliothek",
            back: "Zurück zum Dashboard",
          }
        : {
            title: "Resource Database",
            subtitle:
              "A structured REVEAL library for technical references, supplier intelligence, analytical methodologies, and future BESS frameworks.",
            powered: "8p2 Advisory REVEAL Library",
            back: "Back to dashboard",
          };

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/knowledge-hero.jpg" alt="Resource database hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(110deg,rgba(1,12,20,0.94),rgba(3,22,34,0.78),rgba(7,48,62,0.68))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label={copy.back} />

        <section className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">{copy.powered}</p>
          <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">{copy.title}</h1>
          <p className="max-w-4xl text-sm text-slate-200/80">{copy.subtitle}</p>
        </section>

        <section className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="space-y-3 rounded-[28px] border border-white/10 bg-[rgba(4,18,28,0.72)] p-4 backdrop-blur-sm">
            {resourceSections.map((section) => {
              const isActive = activeSection === section.key;
              return (
                <button
                  key={section.key}
                  type="button"
                  onClick={() => setActiveSection(section.key)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                    isActive
                      ? "border-orange-DEFAULT/55 bg-orange-DEFAULT/15 text-white shadow-[0_14px_28px_rgba(243,146,0,0.18)]"
                      : "border-white/8 bg-white/5 text-slate-300 hover:border-white/20 hover:bg-white/8 hover:text-white"
                  }`}
                >
                  <div className="font-dolfines text-sm font-semibold uppercase tracking-[0.12em]">{section.label}</div>
                </button>
              );
            })}
          </aside>

          <div className="min-w-0">
            {activeSection === "equipment" ? <EquipmentSection lang={lang} /> : null}
            {activeSection === "long-term-distribution" ? <LongTermDistributionSection /> : null}
            {activeSection === "bess-framework" ? <BessFrameworkSection /> : null}
            {activeSection === "optimize-to-p50" ? (
              <SimpleTextSection
                title="Optimize to P50"
                subtitle="This section is reserved for the future client-facing explanation of how REVEAL will normalize measured operating data into an idealized P50 long-term production scenario."
                points={p50Blocks}
              />
            ) : null}
            {activeSection === "reporting-methodology" ? (
              <SimpleTextSection
                title="Reporting Methodology"
                subtitle="This section is reserved for the future client-facing explanation of REVEAL reporting logic, KPI definitions, alert thresholds, and validation workflow."
                points={reportingBlocks}
              />
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
