export interface MonthlyPR {
  month: string; // "2024-01"
  E_act_mwh: number;
  E_ref_mwh: number;
  irrad_kwh_m2: number;
  PR_pct: number;
}

export interface InverterAvailability {
  inv_id: string;
  avail_pct: number;
}

export interface WaterfallItem {
  label: string;
  value_mwh: number;
  type: "base" | "loss" | "gain";
  color?: string; // optional hex override
}

export interface PunchlistItem {
  priority: "HIGH" | "MEDIUM" | "LOW";
  category: string;
  finding: string;
  recommendation: string;
  impact_eur: number | null;
}

export interface AnalysisResult {
  summary: {
    cap_dc_kwp: number;
    cap_ac_kw: number;
    n_inverters: number;
    data_date_range: [string, string];
  };
  pr: {
    monthly: MonthlyPR[];
    annual: Array<{ year: number; E_act_mwh: number; PR_pct: number }>;
    per_inverter: Record<string, number>;
  };
  availability: {
    per_inverter: Record<string, number>;
    site_monthly: Array<{ month: string; avail_pct: number }>;
    per_inverter_monthly: Array<{ month: string; inv_id: string; avail_pct: number }>;
    mean_pct: number;
    whole_site_events: number;
  };
  data_quality: {
    overall_power_pct: number;
    irradiance_pct: number;
    per_inverter: Record<string, number>;
    monthly: Array<{ month: string; inv_id: string; completeness_pct: number; missing_pct: number; frozen_pct: number }>;
    stuck_inverters_count?: number;
  };
  mttf: {
    mean_hours: number;
    events_per_inverter: Record<string, number>;
    by_inverter: Array<{
      inv_id: string;
      n_failures: number;
      mttf_hours: number;
    }>;
  };
  start_stop: Array<{
    inv_id: string;
    start_min: number;
    stop_min: number;
    start_dev: number;
    stop_dev: number;
    start_label: string;
    stop_label: string;
  }>;
  peer_groups: Array<{
    inv_id: string;
    group: string;
    pr_pct: number;
    avail_pct: number;
    start_dev_min: number;
    variability_cv: number;
  }>;
  clipping: {
    site_near_clip_pct: number;
    by_irradiance_bin: Array<{
      label: string;
      near_clip_pct: number;
    }>;
    top_inverters: Array<{
      inv_id: string;
      near_clip_pct: number;
    }>;
  };
  specific_yield: Array<{
    inv_id: string;
    yield_kwh_kwp: number;
    pr_pct: number;
    rank: number;
  }>;
  weather: {
    summary: {
      total_rain_mm: number;
      heavy_rain_days: number;
      very_heavy_rain_days: number;
      max_daily_rain_mm: number;
    } | null;
    monthly: Array<{
      month: string;
      total_rain_mm: number;
      max_hourly_rain_mm: number;
      rainy_hours: number;
      intensity: "dry" | "light" | "moderate" | "heavy" | "very_heavy" | "extreme" | string;
    }>;
    events: Array<{
      date: string;
      total_rain_mm: number;
      peak_hourly_rain_mm: number;
      classification: string;
    }>;
    source: string | null;
    error: string | null;
  };
  waterfall: WaterfallItem[];
  punchlist: PunchlistItem[];
  diagnosis: {
    loss_breakdown: Array<{
      label: string;
      value_mwh: number;
      classification: "recoverable" | "non_recoverable" | "screened";
      color: string;
      commentary: string;
    }>;
    curtailment_candidates: Array<{
      month: string;
      loss_mwh: number;
      irradiation_kwh_m2: number;
      pr_pct: number;
      availability_pct: number;
      confidence: string;
      reason: string;
    }>;
    root_causes: Array<{
      title: string;
      cause: string;
      action: string;
      recoverability: string;
    }>;
    commentary: string[];
    summary: {
      total_gap_mwh: number;
      recoverable_mwh: number;
      non_recoverable_mwh: number;
      over_under_performance_mwh: number;
      design_yield_mwh: number;
      weather_corrected_yield_mwh: number;
      actual_yield_mwh: number;
      screened_bad_data_pct: number;
    };
  };
}

export interface ColumnDetectionResult {
  filename: string;
  columns: string[];
  worksheets?: string[];
  selected_worksheet?: string | null;
  mapping: {
    time?: string;
    power?: string[];
    irradiance?: string;
    ambientTemperature?: string;
    moduleTemperature?: string;
    temperature?: string;
    wind_speed?: string;
    wind_dir?: string;
  };
  row_count: number;
  separator_detected: string;
  data_date_range?: [string, string] | null;
}

export type AnalysisColumnMapping = ColumnDetectionResult["mapping"] & {
  worksheet?: string;
};
