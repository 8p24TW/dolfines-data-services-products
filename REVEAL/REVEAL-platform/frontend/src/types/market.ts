export type PriceForecastScenario = "base" | "high" | "low";

export interface PriceForecastRow {
  year: number;
  avg_price_eur_mwh: number;
  solar_capture_price_eur_mwh: number;
  negative_hours_pct: number;
  negative_hours_estimate: number;
  pv_cannibalization_index: number;
  bess_relief_index: number;
  negative_price_capture_share: number | null;
  negative_price_energy_mwh: number | null;
  site_profile_basis: string;
}

export interface PriceForecastResult {
  scenario: PriceForecastScenario;
  start_year: number;
  end_year: number;
  baseload_start_eur_mwh: number;
  annual_production_mwh: number | null;
  site_profile_basis: string;
  rows: PriceForecastRow[];
  notes: string[];
}

export interface HourlyProfileRow {
  hour: number;
  historical_price_eur_mwh: number | null;
  price_base_eur_mwh: number;
  price_high_eur_mwh: number;
  price_low_eur_mwh: number;
  baseload_base_eur_mwh: number;
  baseload_high_eur_mwh: number;
  baseload_low_eur_mwh: number;
  price_base_p10_eur_mwh: number;
  price_base_p25_eur_mwh: number;
  price_base_p50_eur_mwh: number;
  price_base_p75_eur_mwh: number;
  price_base_p90_eur_mwh: number;
  price_high_p10_eur_mwh: number;
  price_high_p25_eur_mwh: number;
  price_high_p50_eur_mwh: number;
  price_high_p75_eur_mwh: number;
  price_high_p90_eur_mwh: number;
  price_low_p10_eur_mwh: number;
  price_low_p25_eur_mwh: number;
  price_low_p50_eur_mwh: number;
  price_low_p75_eur_mwh: number;
  price_low_p90_eur_mwh: number;
  freq_neg_base: number;
  freq_neg_high: number;
  freq_neg_low: number;
}

export interface HourlyProfileResult {
  year: number;
  month: number;
  day_type: string;
  scenario: string;
  rows: HourlyProfileRow[];
  available: boolean;
  available_scenarios: Array<"base" | "high" | "low">;
  historical_available: boolean;
  type_label?: string;
  month_label?: string;
  error?: string;
}

export interface MarketSiteContext {
  site_id: string;
  has_long_term_output: boolean;
  latest_output_file?: string | null;
  latest_output_generated_at?: string | null;
  average_annual_energy_mwh?: number | null;
  recommendation: string;
}

export interface RetrofitBessResult {
  site_name: string;
  battery_power_kw: number;
  battery_energy_kwh: number;
  battery_duration_hours: number;
  estimated_land_area_m2: number;
  placeholder_capex_eur: number;
  annual_negative_price_energy_mwh: number;
  annual_shifted_energy_mwh: number;
  site_tariff_eur_mwh: number;
  annual_revenue_uplift_eur: number;
  implied_cycles_per_year: number;
  simple_payback_years: number | null;
  recommendation: string;
  notes: string[];
}
