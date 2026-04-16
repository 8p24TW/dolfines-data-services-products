"use client";

import { useMemo, useState, useEffect, Suspense, type MouseEvent as ReactMouseEvent } from "react";
import Image from "next/image";
import { useSearchParams } from "next/navigation";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useSites } from "@/hooks/useSites";
import { api } from "@/lib/api";
import {
  getBessManufacturers,
  getBessModels,
  getBessSpec,
  type BessContainerSpec,
} from "@/lib/equipment-kb";
import type { RetrofitBessResult } from "@/types/market";

// ─── Recommendation engine ─────────────────────────────────────────────────────

interface BessCandidate {
  manufacturer: string;
  model: string;
  spec: BessContainerSpec;
  units: number;
  actualPowerKw: number;
  actualEnergyKwh: number;
  totalCapexEur: number;
  oversizeRatio: number;
  powerCoverageRatio: number;
  score: number;
  reason: string;
}

type SensitivityPoint = {
  shiftedEnergyMwh: number;
  capexEurKwh: number;
  paybackYears: number | null;
  currentCase?: boolean;
  gridX?: number;
  gridY?: number;
};

function calcPayback(capexEur: number, shiftedEnergyMwh: number, tariffEurMwh: number) {
  const uplift = Math.max(shiftedEnergyMwh, 0) * Math.max(tariffEurMwh, 0);
  return uplift > 0 ? capexEur / uplift : null;
}

function formatPaybackCell(value: number | null) {
  return value == null || !Number.isFinite(value) ? "N/A" : `${value.toFixed(1)} yrs`;
}

function getHeatmapColor(value: number | null) {
  if (value == null || !Number.isFinite(value)) return "rgba(71,85,105,0.35)";
  if (value <= 6) return "rgba(52,211,153,0.92)";
  if (value <= 8) return "rgba(132,204,22,0.92)";
  if (value <= 10) return "rgba(250,204,21,0.92)";
  if (value <= 12) return "rgba(251,146,60,0.92)";
  return "rgba(248,113,113,0.92)";
}

function buildRecommendations(targetEnergyKwh: number, targetPowerKw: number): BessCandidate[] {
  const candidates: BessCandidate[] = [];

  for (const mfr of getBessManufacturers()) {
    for (const model of getBessModels(mfr)) {
      const spec = getBessSpec(mfr, model);
      if (!spec) continue;

      const unitsForEnergy = Math.max(1, Math.ceil(targetEnergyKwh / (spec.energy_mwh * 1000)));
      const unitsForPower = targetPowerKw > 0 ? Math.max(1, Math.ceil(targetPowerKw / (spec.power_mw * 1000))) : 1;
      const units = Math.max(unitsForEnergy, unitsForPower);
      const actualEnergyKwh = units * spec.energy_mwh * 1000;
      const actualPowerKw = units * spec.power_mw * 1000;
      const costPerKwh = spec.cost_eur_kwh ?? 200;
      const rte = spec.round_trip_efficiency_pct ?? 88;
      const totalCapexEur = actualEnergyKwh * costPerKwh;
      const oversizeRatio = actualEnergyKwh / targetEnergyKwh;
      const powerCoverageRatio = targetPowerKw > 0 ? actualPowerKw / targetPowerKw : 1;

      // Scoring: lower = better
      const powerPenalty = targetPowerKw > 0 ? Math.abs(powerCoverageRatio - 1) * 120 : 0;
      const fitPenalty = (oversizeRatio - 1) * 60;   // penalise oversizing
      const unitsPenalty = (units - 1) * 5;           // penalise many units
      const rtePenalty = (100 - rte) * 0.8;           // penalise lower efficiency
      const costPenalty = (costPerKwh - 150) * 0.15;  // penalise higher unit cost
      const score = powerPenalty + fitPenalty + unitsPenalty + rtePenalty + costPenalty;

      candidates.push({
        manufacturer: mfr,
        model,
        spec,
        units,
        actualPowerKw,
        actualEnergyKwh,
        totalCapexEur,
        oversizeRatio,
        powerCoverageRatio,
        score,
        reason: "",
      });
    }
  }

  const sorted = [...candidates].sort((a, b) => a.score - b.score).slice(0, 3);
  const maxRte = Math.max(...candidates.map((c) => c.spec.round_trip_efficiency_pct ?? 0));
  const minCapex = Math.min(...candidates.map((c) => c.totalCapexEur));

  return sorted.map((c, i) => {
    const oversizePct = Math.round((c.oversizeRatio - 1) * 100);
    const oversizeLabel = oversizePct > 0 ? `+${oversizePct}% oversize` : "exact match";
    const powerCoveragePct = Math.round(c.powerCoverageRatio * 100);
    let reason: string;

    if (i === 0) {
      reason = `Best overall fit: ${c.units} unit${c.units > 1 ? "s" : ""} delivers ${c.actualPowerKw.toLocaleString()} kW (${powerCoveragePct}% of site MW target) and ${c.actualEnergyKwh.toLocaleString()} kWh (${oversizeLabel}). ${c.spec.chemistry ?? "LFP"}, ${c.spec.round_trip_efficiency_pct ?? 88}% RTE.`;
    } else if (
      (c.spec.round_trip_efficiency_pct ?? 0) === maxRte &&
      maxRte > (sorted[0].spec.round_trip_efficiency_pct ?? 0)
    ) {
      reason = `Highest round-trip efficiency at ${maxRte}% — maximises energy recovered per cycle vs the top-ranked option.`;
    } else if (c.totalCapexEur === minCapex && minCapex < sorted[0].totalCapexEur) {
      reason = `Lowest total CAPEX at EUR ${c.totalCapexEur.toLocaleString()} while still providing ${powerCoveragePct}% of the site MW target and ${c.actualEnergyKwh.toLocaleString()} kWh (${oversizeLabel}).`;
    } else {
      reason = `${c.units} unit${c.units > 1 ? "s" : ""} provides ${c.actualPowerKw.toLocaleString()} kW (${powerCoveragePct}% of site MW target) and ${c.actualEnergyKwh.toLocaleString()} kWh (${oversizeLabel}). ${c.spec.chemistry ?? "LFP"}, ${c.spec.round_trip_efficiency_pct ?? 88}% RTE.`;
    }

    return { ...c, reason };
  });
}

// ─── Component ─────────────────────────────────────────────────────────────────

function RetrofitBessContent() {
  const { sites } = useSites();
  const searchParams = useSearchParams();

  const paramNegEnergy = searchParams.get("neg_energy");
  const paramSiteId = searchParams.get("site_id");
  const paramSiteName = searchParams.get("site_name");

  const [siteId, setSiteId] = useState(paramSiteId ?? "");
  const [negativeEnergyMwh, setNegativeEnergyMwh] = useState(paramNegEnergy ?? "1500");
  const [assumedCyclesPerYear, setAssumedCyclesPerYear] = useState("200");

  // BESS product selection
  const [selectionMode, setSelectionMode] = useState<"auto" | "manual" | null>(null);
  const [selectedMfr, setSelectedMfr] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [autoPickedMfr, setAutoPickedMfr] = useState("");
  const [autoPickedModel, setAutoPickedModel] = useState("");

  const [result, setResult] = useState<RetrofitBessResult | null>(null);
  const [usedProduct, setUsedProduct] = useState<{ mfr: string; model: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sensitivityShiftedEnergyMwh, setSensitivityShiftedEnergyMwh] = useState("");
  const [sensitivityCapexEurKwh, setSensitivityCapexEurKwh] = useState("");
  const [extraTariffUpliftEurMwh, setExtraTariffUpliftEurMwh] = useState("");
  const [hoveredHeatmapPoint, setHoveredHeatmapPoint] = useState<{
    point: SensitivityPoint;
    clientX: number;
    clientY: number;
  } | null>(null);
  const [autoLoadedDefaultCase, setAutoLoadedDefaultCase] = useState(false);

  const fromPerformance = Boolean(paramNegEnergy && paramSiteId);

  useEffect(() => {
    if (paramSiteId) setSiteId(paramSiteId);
    if (paramNegEnergy) setNegativeEnergyMwh(paramNegEnergy);
  }, [paramSiteId, paramNegEnergy]);

  const selectedSite = useMemo(
    () => sites.find((item) => item.id === siteId),
    [siteId, sites],
  );

  const displayName = selectedSite?.display_name ?? paramSiteName ?? null;
  const defaultPrunySite = useMemo(
    () => sites.find((item) => item.display_name.trim().toLowerCase() === "pruny") ?? null,
    [sites],
  );

  useEffect(() => {
    if (fromPerformance || paramSiteId || siteId || !defaultPrunySite) return;
    setSiteId(defaultPrunySite.id);
    setSelectionMode("auto");
  }, [defaultPrunySite, fromPerformance, paramSiteId, siteId]);

  // Target energy for sizing: prefer site data, else estimate from neg-price energy
  const targetEnergyKwh = useMemo(() => {
    if (selectedSite?.retrofit_bess_energy_kwh) return selectedSite.retrofit_bess_energy_kwh;
    const negMwh = Number(negativeEnergyMwh) || 0;
    const cycles = Math.min(330, Math.max(1, Number(assumedCyclesPerYear) || 200));
    return Math.max(100, Math.round((negMwh * 1000) / cycles));
  }, [selectedSite, negativeEnergyMwh, assumedCyclesPerYear]);
  const targetPowerKw = selectedSite?.cap_ac_kw ?? selectedSite?.retrofit_bess_power_kw ?? 0;
  const targetDurationHours = targetPowerKw > 0 ? targetEnergyKwh / targetPowerKw : 0;

  // Auto recommendations
  const recommendations = useMemo(() => {
    if (selectionMode !== "auto") return [];
    return buildRecommendations(targetEnergyKwh, targetPowerKw);
  }, [selectionMode, targetEnergyKwh, targetPowerKw]);

  // Auto-select top recommendation when entering auto mode
  useEffect(() => {
    if (selectionMode === "auto" && recommendations.length > 0 && !autoPickedMfr) {
      setAutoPickedMfr(recommendations[0].manufacturer);
      setAutoPickedModel(recommendations[0].model);
    }
  }, [selectionMode, recommendations, autoPickedMfr]);

  // Clear auto picks when leaving auto mode
  useEffect(() => {
    if (selectionMode !== "auto") {
      setAutoPickedMfr("");
      setAutoPickedModel("");
    }
  }, [selectionMode]);

  const activeMfr = selectionMode === "auto" ? autoPickedMfr : selectedMfr;
  const activeModel = selectionMode === "auto" ? autoPickedModel : selectedModel;

  const activeSpec = useMemo(() => {
    if (!activeMfr || !activeModel) return null;
    return getBessSpec(activeMfr, activeModel) ?? null;
  }, [activeMfr, activeModel]);

  const activeUnits = useMemo(() => {
    if (!activeSpec) return 1;
    const unitsForEnergy = Math.max(1, Math.ceil(targetEnergyKwh / (activeSpec.energy_mwh * 1000)));
    const unitsForPower = targetPowerKw > 0 ? Math.max(1, Math.ceil(targetPowerKw / (activeSpec.power_mw * 1000))) : 1;
    return Math.max(unitsForEnergy, unitsForPower);
  }, [activeSpec, targetEnergyKwh, targetPowerKw]);

  const bessManufacturers = useMemo(() => getBessManufacturers(), []);
  const bessModels = useMemo(
    () => (selectedMfr ? getBessModels(selectedMfr) : []),
    [selectedMfr],
  );

  // Effective battery params for API call
  const effectivePowerKw = activeSpec
    ? activeUnits * activeSpec.power_mw * 1000
    : (selectedSite?.retrofit_bess_power_kw ?? selectedSite?.bess_power_kw ?? 0);

  const effectiveEnergyKwh = activeSpec
    ? activeUnits * activeSpec.energy_mwh * 1000
    : (selectedSite?.retrofit_bess_energy_kwh ?? selectedSite?.bess_energy_kwh ?? 0);

  const effectiveCostEurKwh =
    activeSpec?.cost_eur_kwh ?? selectedSite?.retrofit_bess_cost_eur_kwh ?? 200;

  const effectiveRte =
    activeSpec?.round_trip_efficiency_pct ?? selectedSite?.bess_roundtrip_efficiency_pct ?? 88;

  const effectiveLandM2 = activeSpec
    ? activeUnits * (activeSpec.area_with_access_m2 ?? activeSpec.footprint_m2 ?? 0)
    : (selectedSite?.retrofit_bess_land_area_m2 ?? null);

  const siteTariffEurMwh = selectedSite?.tariff_eur_mwh ?? 0;
  const siteCapacityMw = selectedSite ? (selectedSite.cap_ac_kw ?? 0) / 1000 : 0;

  const liveSensitivity = useMemo(() => {
    if (!result) return null;
    const shiftedEnergyMwh = Math.max(
      0,
      Number(sensitivityShiftedEnergyMwh) || result.annual_shifted_energy_mwh,
    );
    const extraTariffEurMwh = Math.max(0, Number(extraTariffUpliftEurMwh) || 0);
    const baseTariffEurMwh = result.site_tariff_eur_mwh;
    const totalTariffEurMwh = baseTariffEurMwh + extraTariffEurMwh;
    const capexEurKwh = Math.max(
      0,
      Number(sensitivityCapexEurKwh) || effectiveCostEurKwh || 0,
    );
    const capexEur = capexEurKwh * result.battery_energy_kwh;
    const annualUpliftEur = shiftedEnergyMwh * totalTariffEurMwh;
    const paybackYears = annualUpliftEur > 0 ? capexEur / annualUpliftEur : null;
    const maxEnergy = Math.max(
      Math.ceil(result.annual_negative_price_energy_mwh * 1.25),
      Math.ceil(result.annual_shifted_energy_mwh * 1.5),
      Math.ceil(shiftedEnergyMwh * 1.2),
      100,
    );
    const minEnergy = Math.max(100, Math.floor(maxEnergy * 0.35));
    const energySteps = 25;
    const energyValues = Array.from({ length: energySteps }, (_, index) => {
      return Math.round(minEnergy + ((maxEnergy - minEnergy) * index) / (energySteps - 1));
    });
    const minCapex = Math.max(50, Math.floor(Math.min(capexEurKwh, effectiveCostEurKwh || capexEurKwh) * 0.6 / 5) * 5);
    const maxCapex = Math.max(250, Math.ceil(Math.max(capexEurKwh, effectiveCostEurKwh || capexEurKwh, 200) * 1.4 / 5) * 5);
    const capexSteps = 17;
    const capexValues = Array.from({ length: capexSteps }, (_, index) => {
      return Math.round((minCapex + ((maxCapex - minCapex) * index) / (capexSteps - 1)) / 5) * 5;
    });
    const nearestEnergyIndex = energyValues.reduce((bestIndex, value, index, values) => {
      return Math.abs(value - shiftedEnergyMwh) < Math.abs(values[bestIndex] - shiftedEnergyMwh)
        ? index
        : bestIndex;
    }, 0);
    const nearestCapexIndex = capexValues.reduce((bestIndex, value, index, values) => {
      return Math.abs(value - capexEurKwh) < Math.abs(values[bestIndex] - capexEurKwh)
        ? index
        : bestIndex;
    }, 0);
    const chartData: SensitivityPoint[] = [];
    for (const [capexIndex, capexValue] of capexValues.entries()) {
      for (const [energyIndex, energyValue] of energyValues.entries()) {
        chartData.push({
          shiftedEnergyMwh: energyValue,
          capexEurKwh: capexValue,
          paybackYears: calcPayback(capexValue * result.battery_energy_kwh, energyValue, totalTariffEurMwh),
          currentCase: energyIndex === nearestEnergyIndex && capexIndex === nearestCapexIndex,
          gridX: energyIndex,
          gridY: capexIndex,
        });
      }
    }
    return {
      shiftedEnergyMwh,
      baseTariffEurMwh,
      extraTariffEurMwh,
      totalTariffEurMwh,
      capexEurKwh,
      capexEur,
      annualUpliftEur,
      paybackYears,
      chartData,
      energyValues,
      capexValues,
      energyDomain: [minEnergy, maxEnergy] as [number, number],
      capexDomain: [minCapex, maxCapex] as [number, number],
    };
  }, [
    result,
    sensitivityShiftedEnergyMwh,
    sensitivityCapexEurKwh,
    extraTariffUpliftEurMwh,
    effectiveCostEurKwh,
  ]);

  async function runRetrofit() {
    if (!selectedSite && !paramSiteName) {
      setError("Select a site first.");
      return;
    }
    if (selectedSite && (selectedSite.tariff_eur_mwh == null || selectedSite.tariff_eur_mwh <= 0)) {
      setError("Add a valid site tariff in the site setup before running the retrofit BESS screening.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await api.market.retrofitBess({
        site_id: selectedSite?.id ?? paramSiteId ?? undefined,
        site_name: selectedSite?.display_name ?? paramSiteName ?? "Site",
        annual_production_mwh: selectedSite?.expected_aep_gwh
          ? selectedSite.expected_aep_gwh * 1000
          : null,
        annual_negative_price_energy_mwh: Number(negativeEnergyMwh),
        battery_power_kw: effectivePowerKw,
        battery_energy_kwh: effectiveEnergyKwh,
        battery_cost_eur_kwh: effectiveCostEurKwh,
        battery_roundtrip_efficiency_pct: effectiveRte,
        site_tariff_eur_mwh: siteTariffEurMwh,
        estimated_land_area_m2: effectiveLandM2,
      });
      setResult(response);
      setUsedProduct(activeMfr && activeModel ? { mfr: activeMfr, model: activeModel } : null);
      setSensitivityShiftedEnergyMwh(response.annual_shifted_energy_mwh.toFixed(0));
      const initialCapexPerKwh = response.battery_energy_kwh > 0
        ? response.placeholder_capex_eur / response.battery_energy_kwh
        : effectiveCostEurKwh;
      setSensitivityCapexEurKwh(initialCapexPerKwh.toFixed(0));
      setExtraTariffUpliftEurMwh("0");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to evaluate retrofit BESS case.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (autoLoadedDefaultCase || fromPerformance || paramSiteId) return;
    if (!selectedSite || selectedSite.id !== defaultPrunySite?.id) return;
    if (!selectionMode) {
      setSelectionMode("auto");
      return;
    }
    if (selectionMode === "auto" && recommendations.length > 0 && !autoPickedMfr) return;
    if (loading || result || error) return;
    setAutoLoadedDefaultCase(true);
    void runRetrofit();
  }, [
    autoLoadedDefaultCase,
    autoPickedMfr,
    defaultPrunySite?.id,
    error,
    fromPerformance,
    loading,
    paramSiteId,
    recommendations.length,
    result,
    selectedSite,
    selectionMode,
  ]);

  function handleHeatmapMove(event: ReactMouseEvent<HTMLDivElement>) {
    if (!liveSensitivity) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const svgWidth = rect.width;
    const svgHeight = rect.height;
    const margin = { top: 16, right: 20, bottom: 42, left: 64 };
    const plotWidth = svgWidth - margin.left - margin.right;
    const plotHeight = svgHeight - margin.top - margin.bottom;
    if (plotWidth <= 0 || plotHeight <= 0) return;

    const localX = Math.min(Math.max(event.clientX - rect.left - margin.left, 0), plotWidth);
    const localY = Math.min(Math.max(event.clientY - rect.top - margin.top, 0), plotHeight);
    const xRatio = localX / plotWidth;
    const yRatio = localY / plotHeight;

    const energyIndex = Math.min(
      liveSensitivity.energyValues.length - 1,
      Math.max(0, Math.round(xRatio * (liveSensitivity.energyValues.length - 1))),
    );
    const capexIndexFromTop = Math.min(
      liveSensitivity.capexValues.length - 1,
      Math.max(0, Math.round(yRatio * (liveSensitivity.capexValues.length - 1))),
    );
    const capexIndex = liveSensitivity.capexValues.length - 1 - capexIndexFromTop;
    const point = liveSensitivity.chartData.find(
      (item) => item.gridX === energyIndex && item.gridY === capexIndex,
    );
    if (!point) return;
    setHoveredHeatmapPoint({
      point,
      clientX: event.clientX,
      clientY: event.clientY,
    });
  }

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image
          src="/brand/login-hero.jpg"
          alt="Retrofit BESS background"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.94),rgba(5,30,45,0.82),rgba(240,120,32,0.12))]" />
      </div>
      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label="Back to dashboard" />

        <section className="rounded-[30px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">
            REVEAL retrofit screening
          </p>
          <h1 className="font-dolfines mt-3 text-3xl font-semibold tracking-[0.08em] text-white">
            Retrofit BESS Calculator
          </h1>
          <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-200/84">
            First-pass screening for storage retrofit cases. Select a BESS product from the
            equipment database — or let REVEAL auto-recommend the best fit — then run the
            analysis using negative-price energy from the Performance workflow or entered manually.
            REVEAL assumes a one-directional retrofit BESS that stores curtailed on-site energy and re-injects it at the site's saved tariff.
          </p>
        </section>

        {fromPerformance ? (
          <div className="rounded-[22px] border border-emerald-300/20 bg-emerald-500/8 px-5 py-3">
            <p className="text-sm font-semibold text-white">
              Pre-populated from Performance analysis
            </p>
            <p className="mt-1 text-xs text-slate-300/80">
              Negative-price energy ({Number(paramNegEnergy).toLocaleString()} MWh/yr) and site
              pre-filled from the Performance tab.
              {displayName ? ` Site: ${displayName}.` : ""}
              {" "}Adjust any value before running.
            </p>
          </div>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          {/* ── Left panel: inputs ── */}
          <div className="space-y-4 rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">

            {/* Site */}
            <label className="block space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Site</span>
              <select
                className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100"
                value={siteId}
                onChange={(e) => setSiteId(e.target.value)}
              >
                <option value="">Select site</option>
                {sites.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.display_name}
                  </option>
                ))}
              </select>
            </label>

            {selectedSite && !fromPerformance ? (
              <div className="rounded-2xl border border-amber-300/20 bg-amber-500/8 px-4 py-3">
                <p className="text-sm font-semibold text-white">
                  Performance analysis recommended first
                </p>
                <p className="mt-1 text-xs leading-6 text-slate-300/82">
                  We recommend you run the Performance analysis first to analyse the negative-hour losses for {selectedSite.display_name}. Otherwise, add in your calculated estimate below and continue with this retrofit screening.
                </p>
              </div>
            ) : null}

            {/* Negative energy */}
            <label className="block space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">
                Annual negative-price energy to recover (MWh/yr)
              </span>
              <input
                className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100"
                value={negativeEnergyMwh}
                onChange={(e) => setNegativeEnergyMwh(e.target.value)}
              />
              {fromPerformance ? (
                <span className="text-xs text-emerald-300">
                  Derived from the Performance negative-price exposure analysis.
                </span>
              ) : (
                <span className="text-xs text-slate-400">
                  Run the Performance negative-price exposure analysis to calculate this
                  automatically, or enter a value manually.
                </span>
              )}
            </label>

            {!selectedSite?.retrofit_bess_energy_kwh ? (
              <label className="block space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">
                  Assumed full cycles per year for auto-sizing
                </span>
                <input
                  className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100"
                  value={assumedCyclesPerYear}
                  onChange={(e) => setAssumedCyclesPerYear(e.target.value)}
                />
                <span className="text-xs text-slate-400">
                  Target energy = annual negative-price energy / cycles per year. With{" "}
                  {Number(negativeEnergyMwh || 0).toLocaleString()} MWh/yr and{" "}
                  {Math.min(330, Math.max(1, Number(assumedCyclesPerYear) || 200)).toLocaleString()} cycles/yr,
                  REVEAL sizes to about {targetEnergyKwh.toLocaleString()} kWh. Auto-recommend then checks this against the full site export power target of {(targetPowerKw / 1000).toLocaleString()} MW.
                </span>
              </label>
            ) : (
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
                <p>
                  <span className="text-slate-400">Configured retrofit energy:</span>{" "}
                  {selectedSite.retrofit_bess_energy_kwh.toLocaleString()} kWh
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Auto-recommend uses the retrofit BESS energy stored on this site instead of the generic annual-energy sizing assumption.
                </p>
              </div>
            )}

            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
              <p>
                <span className="text-slate-400">Site tariff:</span>{" "}
                {selectedSite?.tariff_eur_mwh != null ? `${selectedSite.tariff_eur_mwh.toLocaleString()} EUR/MWh` : "Not set"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Retrofit BESS revenue is based on the site's saved tariff, assuming the battery only stores curtailed on-site generation and cannot charge from the grid.
              </p>
            </div>

            {/* ── BESS product selection ── */}
            <div className="space-y-3 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">BESS Product</span>
                {activeSpec && (
                  <span className="rounded-full bg-orange-DEFAULT/20 px-2.5 py-0.5 text-xs font-medium text-orange-200">
                    {activeMfr} {activeModel}
                  </span>
                )}
              </div>

              {/* Mode toggle */}
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectionMode(selectionMode === "auto" ? null : "auto")}
                  className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    selectionMode === "auto"
                      ? "bg-orange-DEFAULT/20 text-orange-200 ring-1 ring-orange-DEFAULT/40"
                      : "bg-white/6 text-slate-300 hover:bg-white/10"
                  }`}
                >
                  Auto-recommend
                </button>
                <button
                  onClick={() => setSelectionMode(selectionMode === "manual" ? null : "manual")}
                  className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    selectionMode === "manual"
                      ? "bg-orange-DEFAULT/20 text-orange-200 ring-1 ring-orange-DEFAULT/40"
                      : "bg-white/6 text-slate-300 hover:bg-white/10"
                  }`}
                >
                  Select manually
                </button>
              </div>

              {selectionMode === "auto" && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-400">
                    Ranked for a{" "}
                    <span className="text-slate-200">{(targetPowerKw / 1000).toLocaleString()} MW</span>{" "}
                    site power target and{" "}
                    <span className="text-slate-200">{targetEnergyKwh.toLocaleString()} kWh</span>{" "}
                    storage target
                    {selectedSite?.retrofit_bess_energy_kwh
                      ? " (from site configuration)"
                      : ` (estimated from ${Number(negativeEnergyMwh || 0).toLocaleString()} MWh/yr divided by ${Math.min(330, Math.max(1, Number(assumedCyclesPerYear) || 200)).toLocaleString()} cycles/yr)`}
                    . This corresponds to about {targetDurationHours.toFixed(2)} hours at 100% of site AC export capacity.
                  </p>
                  {recommendations.map((rec, i) => {
                    const isActive =
                      autoPickedMfr === rec.manufacturer && autoPickedModel === rec.model;
                    return (
                      <button
                        key={`${rec.manufacturer}-${rec.model}`}
                        onClick={() => {
                          setAutoPickedMfr(rec.manufacturer);
                          setAutoPickedModel(rec.model);
                        }}
                        className={`w-full rounded-xl border p-3 text-left transition-colors ${
                          isActive
                            ? "border-orange-DEFAULT/50 bg-orange-DEFAULT/10"
                            : "border-white/10 bg-white/4 hover:border-white/20 hover:bg-white/6"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-semibold text-white">
                            {i === 0 ? (
                              <span className="mr-1.5 text-orange-300">#1</span>
                            ) : (
                              <span className="mr-1.5 text-slate-400">#{i + 1}</span>
                            )}
                            {rec.manufacturer} {rec.model}
                          </span>
                          <span className="shrink-0 text-xs text-slate-400">
                            {rec.units} unit{rec.units > 1 ? "s" : ""} ·{" "}
                            {rec.actualEnergyKwh.toLocaleString()} kWh
                          </span>
                        </div>
                        <p className="mt-1 text-xs leading-5 text-slate-300">{rec.reason}</p>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-400">
                          <span>RTE {rec.spec.round_trip_efficiency_pct ?? 88}%</span>
                          <span>EUR {rec.spec.cost_eur_kwh ?? 200}/kWh</span>
                          <span>CAPEX EUR {rec.totalCapexEur.toLocaleString()}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {selectionMode === "manual" && (
                <div className="space-y-2">
                  <select
                    className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100"
                    value={selectedMfr}
                    onChange={(e) => {
                      setSelectedMfr(e.target.value);
                      setSelectedModel("");
                    }}
                  >
                    <option value="">Select manufacturer</option>
                    {bessManufacturers.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  {selectedMfr && (
                    <select
                      className="w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100"
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                    >
                      <option value="">Select model</option>
                      {bessModels.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* Active product spec card */}
              {activeSpec && (
                <div className="rounded-xl border border-orange-DEFAULT/25 bg-orange-DEFAULT/8 p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-300/70">
                    Selected product
                  </p>
                  <p className="mt-1 text-sm font-semibold text-white">
                    {activeMfr} · {activeModel}
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-y-0.5 text-xs text-slate-300">
                    <span>
                      <span className="text-slate-400">Power: </span>
                      {(activeUnits * activeSpec.power_mw).toLocaleString()} MW
                    </span>
                    <span>
                      <span className="text-slate-400">Energy: </span>
                      {(activeUnits * activeSpec.energy_mwh).toLocaleString()} MWh
                    </span>
                    <span>
                      <span className="text-slate-400">Site AC capacity: </span>
                      {siteCapacityMw.toLocaleString()} MW
                    </span>
                    <span>
                      <span className="text-slate-400">RTE: </span>
                      {activeSpec.round_trip_efficiency_pct ?? 88}%
                    </span>
                    <span>
                      <span className="text-slate-400">Cost: </span>
                      EUR {activeSpec.cost_eur_kwh ?? 200}/kWh
                    </span>
                    {activeUnits > 1 && (
                      <span className="col-span-2 text-slate-400">
                        {activeUnits} units · footprint ~
                        {effectiveLandM2 ? `${effectiveLandM2} m²` : "n/a"}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Site candidate data (shown as fallback when no product selected) */}
            {!activeSpec && selectedSite ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                <p className="mb-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                  Site candidate (placeholder)
                </p>
                <p>
                  <span className="text-slate-400">Power:</span>{" "}
                  {((selectedSite.retrofit_bess_power_kw ?? 0) / 1000).toLocaleString()} MW
                </p>
                <p>
                  <span className="text-slate-400">Energy:</span>{" "}
                  {((selectedSite.retrofit_bess_energy_kwh ?? 0) / 1000).toLocaleString()} MWh
                </p>
                <p>
                  <span className="text-slate-400">Site AC capacity:</span>{" "}
                  {siteCapacityMw.toLocaleString()} MW
                </p>
                <p>
                  <span className="text-slate-400">Capex:</span> EUR{" "}
                  {selectedSite.retrofit_bess_cost_eur_kwh ?? 200}/kWh
                </p>
                <p>
                  <span className="text-slate-400">Land area:</span>{" "}
                  {selectedSite.retrofit_bess_land_area_m2 ?? 0} m²
                </p>
              </div>
            ) : null}

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              loading={loading}
              onClick={runRetrofit}
            >
              Evaluate retrofit case
            </Button>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
          </div>

          {/* ── Right panel: results ── */}
          <div className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">
            {!result ? (
              <p className="text-sm leading-7 text-slate-300/82">
                Select a site, choose a BESS product from the equipment database (or use
                Auto-recommend), then run the first-pass screening. Use the Performance tab to
                derive negative-price energy automatically, or enter a value directly.
              </p>
            ) : (
              <div className="space-y-5">
                {usedProduct && (
                  <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/4 px-4 py-2 text-xs text-slate-300">
                    <span className="text-slate-400">Product evaluated:</span>
                    <span className="font-semibold text-white">
                      {usedProduct.mfr} {usedProduct.model}
                    </span>
                    <span className="text-slate-400">
                      · { (effectivePowerKw / 1000).toLocaleString() } MW / { (effectiveEnergyKwh / 1000).toLocaleString() } MWh
                      {selectedSite ? ` · Site ${siteCapacityMw.toLocaleString()} MW AC` : ""}
                    </span>
                  </div>
                )}

                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">CAPEX</p>
                    <p className="mt-2 text-xl font-semibold text-white">
                      EUR {result.placeholder_capex_eur.toLocaleString()}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Annual uplift</p>
                    <p className="mt-2 text-xl font-semibold text-white">
                      EUR {result.annual_revenue_uplift_eur.toLocaleString()}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Payback</p>
                    <p className="mt-2 text-xl font-semibold text-white">
                      {result.simple_payback_years != null
                        ? `${result.simple_payback_years.toFixed(1)} yrs`
                        : "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Land area</p>
                    <p className="mt-2 text-xl font-semibold text-white">
                      {result.estimated_land_area_m2.toFixed(0)} m²
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-orange-DEFAULT/35 bg-orange-DEFAULT/10 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-orange-200">
                    Recommendation
                  </p>
                  <p className="mt-2 text-sm leading-7 text-orange-50">{result.recommendation}</p>
                </div>

                <div className="rounded-[24px] border border-white/12 bg-[rgba(3,16,26,0.78)] p-5">
                  <div className="mb-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                        Sensitivity analysis
                      </p>
                      <p className="mt-1 text-sm text-slate-300/82">
                        Explore how profitability changes as recovered energy and BESS capex move. Base site tariff stays fixed; an optional extra tariff uplift can be added if shifting injection creates additional value in higher-priced hours.
                      </p>
                    </div>
                  </div>

                  {liveSensitivity ? (
                    <div className="mb-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Base site tariff</p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {liveSensitivity.baseTariffEurMwh.toFixed(1)} EUR/MWh
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Extra tariff uplift</p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {liveSensitivity.extraTariffEurMwh.toFixed(1)} EUR/MWh
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Total value basis</p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {liveSensitivity.totalTariffEurMwh.toFixed(1)} EUR/MWh
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Live payback</p>
                        <p className="mt-2 text-lg font-semibold text-white">
                          {formatPaybackCell(liveSensitivity.paybackYears)}
                        </p>
                      </div>
                    </div>
                  ) : null}

                  {liveSensitivity ? (
                    <div className="mb-5 grid gap-3 md:grid-cols-3">
                      <label className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        <span className="font-semibold text-white">Annual shifted energy</span>
                        <input
                          type="range"
                          min={0}
                          max={Math.max(
                            Math.ceil(result.annual_negative_price_energy_mwh * 1.2),
                            Math.ceil(result.annual_shifted_energy_mwh * 1.5),
                            100,
                          )}
                          step={25}
                          value={Number(sensitivityShiftedEnergyMwh) || 0}
                          onChange={(e) => setSensitivityShiftedEnergyMwh(e.target.value)}
                          className="mt-3 w-full accent-orange-DEFAULT"
                        />
                        <div className="mt-2 flex items-center justify-between text-xs">
                          <span className="text-slate-400">Scenario value</span>
                          <span className="font-semibold text-white">
                            {liveSensitivity.shiftedEnergyMwh.toLocaleString()} MWh/yr
                          </span>
                        </div>
                      </label>
                      <label className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        <span className="font-semibold text-white">Capex ceiling</span>
                        <input
                          type="range"
                          min={50}
                          max={400}
                          step={5}
                          value={Number(sensitivityCapexEurKwh) || 0}
                          onChange={(e) => setSensitivityCapexEurKwh(e.target.value)}
                          className="mt-3 w-full accent-orange-DEFAULT"
                        />
                        <div className="mt-2 flex items-center justify-between text-xs">
                          <span className="text-slate-400">Scenario value</span>
                          <span className="font-semibold text-white">
                            {liveSensitivity.capexEurKwh.toFixed(0)} EUR/kWh
                          </span>
                        </div>
                      </label>
                      <label className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        <span className="font-semibold text-white">Extra tariff uplift (if applicable)</span>
                        <input
                          type="range"
                          min={0}
                          max={40}
                          step={0.5}
                          value={Number(extraTariffUpliftEurMwh) || 0}
                          onChange={(e) => setExtraTariffUpliftEurMwh(e.target.value)}
                          className="mt-3 w-full accent-orange-DEFAULT"
                        />
                        <div className="mt-2 flex items-center justify-between text-xs">
                          <span className="text-slate-400">Scenario value</span>
                          <span className="font-semibold text-white">
                            {liveSensitivity.extraTariffEurMwh.toFixed(1)} EUR/MWh
                          </span>
                        </div>
                      </label>
                    </div>
                  ) : null}

                  <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                        Payback heatmap
                      </p>
                      {liveSensitivity ? (
                        <div
                          className="relative h-[340px] w-full overflow-hidden rounded-xl border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01))]"
                          onMouseMove={handleHeatmapMove}
                          onMouseLeave={() => setHoveredHeatmapPoint(null)}
                        >
                          <svg viewBox="0 0 720 340" className="h-full w-full">
                            {(() => {
                              const margin = { top: 16, right: 20, bottom: 42, left: 64 };
                              const plotWidth = 720 - margin.left - margin.right;
                              const plotHeight = 340 - margin.top - margin.bottom;
                              const xValues = liveSensitivity.energyValues;
                              const yValues = liveSensitivity.capexValues;
                              const cellWidth = plotWidth / xValues.length;
                              const cellHeight = plotHeight / yValues.length;
                              const xTicks = [
                                xValues[0],
                                xValues[Math.floor((xValues.length - 1) * 0.25)],
                                xValues[Math.floor((xValues.length - 1) * 0.5)],
                                xValues[Math.floor((xValues.length - 1) * 0.75)],
                                xValues[xValues.length - 1],
                              ];
                              const yTicks = [
                                yValues[0],
                                yValues[Math.floor((yValues.length - 1) * 0.33)],
                                yValues[Math.floor((yValues.length - 1) * 0.66)],
                                yValues[yValues.length - 1],
                              ];
                              const hovered = hoveredHeatmapPoint?.point ?? null;
                              const hoveredX = hovered ? margin.left + ((hovered.gridX ?? 0) + 0.5) * cellWidth : null;
                              const hoveredY = hovered
                                ? margin.top + (yValues.length - (hovered.gridY ?? 0) - 0.5) * cellHeight
                                : null;
                              return (
                                <>
                                  <defs>
                                    <linearGradient id="heatmap-bg" x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="0%" stopColor="rgba(255,255,255,0.04)" />
                                      <stop offset="100%" stopColor="rgba(255,255,255,0.01)" />
                                    </linearGradient>
                                  </defs>
                                  <rect x={margin.left} y={margin.top} width={plotWidth} height={plotHeight} rx={16} fill="url(#heatmap-bg)" />
                                  {xTicks.map((tick) => {
                                    const xIndex = xValues.indexOf(tick);
                                    const x = margin.left + (xIndex + 0.5) * cellWidth;
                                    return (
                                      <g key={`x-${tick}`}>
                                        <line x1={x} x2={x} y1={margin.top} y2={margin.top + plotHeight} stroke="rgba(255,255,255,0.08)" strokeDasharray="3 4" />
                                        <text x={x} y={margin.top + plotHeight + 22} textAnchor="middle" fill="#94a3b8" fontSize="11">
                                          {tick.toLocaleString()}
                                        </text>
                                      </g>
                                    );
                                  })}
                                  {yTicks.map((tick) => {
                                    const yIndex = yValues.indexOf(tick);
                                    const y = margin.top + (yValues.length - yIndex - 0.5) * cellHeight;
                                    return (
                                      <g key={`y-${tick}`}>
                                        <line x1={margin.left} x2={margin.left + plotWidth} y1={y} y2={y} stroke="rgba(255,255,255,0.08)" strokeDasharray="3 4" />
                                        <text x={margin.left - 10} y={y + 4} textAnchor="end" fill="#94a3b8" fontSize="11">
                                          {tick}
                                        </text>
                                      </g>
                                    );
                                  })}
                                  {liveSensitivity.chartData.map((point) => {
                                    const x = margin.left + (point.gridX ?? 0) * cellWidth;
                                    const y = margin.top + (yValues.length - (point.gridY ?? 0) - 1) * cellHeight;
                                    return (
                                      <rect
                                        key={`${point.shiftedEnergyMwh}-${point.capexEurKwh}`}
                                        x={x}
                                        y={y}
                                        width={cellWidth + 0.5}
                                        height={cellHeight + 0.5}
                                        fill={getHeatmapColor(point.paybackYears)}
                                        opacity={0.96}
                                      />
                                    );
                                  })}
                                  {hoveredX != null && hoveredY != null ? (
                                    <g>
                                      <line x1={hoveredX} x2={hoveredX} y1={margin.top} y2={margin.top + plotHeight} stroke="rgba(255,255,255,0.8)" strokeWidth="1.2" />
                                      <line x1={margin.left} x2={margin.left + plotWidth} y1={hoveredY} y2={hoveredY} stroke="rgba(255,255,255,0.8)" strokeWidth="1.2" />
                                      <circle cx={hoveredX} cy={hoveredY} r="5" fill="rgba(255,255,255,0.95)" />
                                    </g>
                                  ) : null}
                                  {liveSensitivity.chartData
                                    .filter((point) => point.currentCase)
                                    .map((point) => {
                                      const x = margin.left + ((point.gridX ?? 0) + 0.5) * cellWidth;
                                      const y = margin.top + (yValues.length - (point.gridY ?? 0) - 0.5) * cellHeight;
                                      return (
                                        <rect
                                          key={`current-${point.shiftedEnergyMwh}-${point.capexEurKwh}`}
                                          x={x - cellWidth / 2}
                                          y={y - cellHeight / 2}
                                          width={cellWidth}
                                          height={cellHeight}
                                          fill="none"
                                          stroke="rgba(255,255,255,0.95)"
                                          strokeWidth="2"
                                        />
                                      );
                                    })}
                                  <text
                                    x={margin.left + plotWidth / 2}
                                    y={334}
                                    textAnchor="middle"
                                    fill="#94a3b8"
                                    fontSize="11"
                                  >
                                    Recovered energy (MWh/yr)
                                  </text>
                                  <text
                                    x={18}
                                    y={margin.top + plotHeight / 2}
                                    textAnchor="middle"
                                    fill="#94a3b8"
                                    fontSize="11"
                                    transform={`rotate(-90 18 ${margin.top + plotHeight / 2})`}
                                  >
                                    Capex (EUR/kWh)
                                  </text>
                                </>
                              );
                            })()}
                          </svg>
                          {hoveredHeatmapPoint ? (
                            <div
                              className="pointer-events-none absolute z-10 min-w-[220px] rounded-2xl border border-orange-300/20 bg-[rgba(3,16,26,0.96)] px-4 py-3 text-xs text-slate-200 shadow-[0_18px_40px_rgba(0,0,0,0.28)]"
                              style={{
                                left: 16,
                                top: 16,
                              }}
                            >
                              <p className="font-semibold text-white">Heatmap cursor</p>
                              <p className="mt-2"><span className="text-slate-400">Recovered energy:</span> {hoveredHeatmapPoint.point.shiftedEnergyMwh.toLocaleString()} MWh/yr</p>
                              <p><span className="text-slate-400">Capex:</span> {hoveredHeatmapPoint.point.capexEurKwh.toFixed(0)} EUR/kWh</p>
                              <p><span className="text-slate-400">Payback:</span> {formatPaybackCell(hoveredHeatmapPoint.point.paybackYears)}</p>
                              <p><span className="text-slate-400">Value basis:</span> {liveSensitivity.totalTariffEurMwh.toFixed(1)} EUR/MWh</p>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
                        <span className="text-slate-400">Payback bands</span>
                        <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-[rgba(52,211,153,0.92)]" />≤6y</span>
                        <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-[rgba(132,204,22,0.92)]" />6-8y</span>
                        <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-[rgba(250,204,21,0.92)]" />8-10y</span>
                        <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-[rgba(251,146,60,0.92)]" />10-12y</span>
                        <span className="inline-flex items-center gap-1"><span className="h-3 w-3 rounded-sm bg-[rgba(248,113,113,0.92)]" />{" >12y"}</span>
                        <span className="inline-flex items-center gap-1 text-white"><span className="h-3 w-3 rounded-sm border border-white/90 bg-transparent" />Current case</span>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                        Live scenario
                      </p>
                      <div className="space-y-3 text-sm text-slate-200">
                        <div className="rounded-xl border border-white/8 bg-white/4 p-3">
                          <p><span className="text-slate-400">Annual shifted energy:</span> {liveSensitivity?.shiftedEnergyMwh.toLocaleString()} MWh/yr</p>
                          <p><span className="text-slate-400">Base site tariff:</span> {liveSensitivity?.baseTariffEurMwh.toFixed(1)} EUR/MWh</p>
                          <p><span className="text-slate-400">Extra tariff uplift:</span> {liveSensitivity?.extraTariffEurMwh.toFixed(1)} EUR/MWh</p>
                          <p><span className="text-slate-400">Total value basis:</span> {liveSensitivity?.totalTariffEurMwh.toFixed(1)} EUR/MWh</p>
                          <p><span className="text-slate-400">Capex ceiling:</span> {liveSensitivity?.capexEurKwh.toFixed(0)} EUR/kWh</p>
                          <p><span className="text-slate-400">Scenario CAPEX:</span> EUR {liveSensitivity?.capexEur.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                          <p><span className="text-slate-400">Annual uplift:</span> EUR {liveSensitivity?.annualUpliftEur.toLocaleString(undefined, { maximumFractionDigits: 0 })}/yr</p>
                          <p><span className="text-slate-400">Simple payback:</span> {formatPaybackCell(liveSensitivity?.paybackYears ?? null)}</p>
                        </div>
                        <p className="text-xs leading-6 text-slate-400">
                          The heatmap shows how payback changes across combinations of recovered energy and BESS capex. The base site tariff stays fixed, while the optional extra tariff uplift can represent added value from shifting injection into stronger-priced hours.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                    <p>
                      <span className="text-slate-400">Neg-price energy input:</span>{" "}
                      {result.annual_negative_price_energy_mwh.toFixed(1)} MWh/yr
                    </p>
                    <p>
                      <span className="text-slate-400">Shiftable energy:</span>{" "}
                      {result.annual_shifted_energy_mwh.toFixed(1)} MWh/yr
                    </p>
                    <p>
                      <span className="text-slate-400">Tariff basis:</span>{" "}
                      {result.site_tariff_eur_mwh.toFixed(1)} EUR/MWh site tariff
                    </p>
                    <p>
                      <span className="text-slate-400">Implied cycles:</span>{" "}
                      {result.implied_cycles_per_year.toFixed(1)} cycles/yr
                    </p>
                    <p>
                      <span className="text-slate-400">Battery duration:</span>{" "}
                      {result.battery_duration_hours.toFixed(2)} h
                    </p>
                    <p>
                      <span className="text-slate-400">BESS size:</span>{" "}
                      {(result.battery_power_kw / 1000).toFixed(2)} MW / {(result.battery_energy_kwh / 1000).toFixed(2)} MWh
                    </p>
                    {selectedSite ? (
                      <p>
                        <span className="text-slate-400">Site AC capacity:</span>{" "}
                        {siteCapacityMw.toLocaleString()} MW
                      </p>
                    ) : null}
                    <p>
                      <span className="text-slate-400">Payback basis:</span>{" "}
                      EUR {result.placeholder_capex_eur.toLocaleString()} / EUR {result.annual_revenue_uplift_eur.toLocaleString()} per year
                    </p>
                    <p className="text-slate-400">
                      Annual uplift = {result.annual_shifted_energy_mwh.toFixed(1)} MWh/yr x {result.site_tariff_eur_mwh.toFixed(1)} EUR/MWh
                      = EUR {result.annual_revenue_uplift_eur.toLocaleString()}/yr.
                    </p>
                    <p className="mt-2 text-slate-400">
                      Simple payback = placeholder CAPEX / annual uplift, where annual uplift = annual shifted energy x site tariff.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                    {result.notes.map((note) => (
                      <p key={note} className="leading-7">
                        {note}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function RetrofitBessPage() {
  return (
    <Suspense>
      <RetrofitBessContent />
    </Suspense>
  );
}
