export type LongTermCorrelationStatus = "queued" | "running" | "complete" | "error";

export type LongTermChartPoint = {
  year?: number;
  month?: number;
  mode: string;
  energy_mwh: number;
  irradiation_kwh_m2?: number;
};

export type LongTermIrradianceFitPoint = {
  reference_irradiance_kwh_m2: number;
  site_irradiance_kwh_m2: number;
};

export type LongTermCorrelationJob = {
  jobId: string;
  siteId: string;
  status: LongTermCorrelationStatus;
  runMode?: "screening" | "preview" | "projection";
  progress: number;
  stage?: string;
  error?: string;
  outputFormat: "csv" | "xlsx";
  downloadUrl?: string;
  fileName?: string;
  summary?: {
    siteType: string;
    measuredStart: string;
    measuredEnd: string;
    correlationYears: number;
    measuredDurationYears?: number;
    siteTimezone?: string;
    fullMeasuredYears?: number;
    projectionStart?: string;
    measuredTotalEnergyMwh?: number;
    measuredAnnualizedAepMwh?: number;
    projectedAverageAepMwh?: number;
    measuredSpecificYieldKwhKwp?: number | null;
    projectedSpecificYieldKwhKwp?: number | null;
    yieldScenario?: string;
    specificYieldInputKwhKwp?: number | null;
    dcCapacityKwp?: number | null;
    acCapacityKw?: number | null;
    referenceIrradianceMode?: string;
    irradianceFitR2?: number;
    irradianceFitSlope?: number;
    irradianceFitIntercept?: number;
    irradianceFitPoints?: number;
    irradianceFitAggregation?: string;
    irradianceFitTotalDays?: number;
    irradianceFitMatchedDays?: number;
    irradianceFitExcludedDays?: number;
    badDataRule?: string;
    badDataMinimumConsecutiveRows?: number;
    totalMeasuredRows?: number;
    badDataRows?: number;
    badDataHours?: number;
    badDataEvents?: number;
    badPowerRows?: number;
    badWeatherRows?: number;
    badPowerEvents?: number;
    badWeatherEvents?: number;
    badDataApplied?: boolean;
    badPowerDates?: string[];
    badWeatherDates?: string[];
    badPowerWindows?: Array<{
      start: string;
      end: string;
      rowCount: number;
      durationHours: number;
      stuckPowerKw?: number | null;
    }>;
    badWeatherWindows?: Array<{
      start: string;
      end: string;
      rowCount: number;
      durationHours: number;
      stuckIrradiance?: number | null;
    }>;
    selectedPowerChannels: number;
    selectedPowerColumnNames?: string[];
    referenceSource: string;
    referenceDataset: string;
    note?: string;
  };
  charts?: {
    annualEnergy: LongTermChartPoint[];
    monthlyEnergy: LongTermChartPoint[];
    irradianceFit?: LongTermIrradianceFitPoint[];
  };
};
