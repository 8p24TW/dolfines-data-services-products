export type SiteStatus = "operational" | "maintenance" | "offline";
export type SiteType = "solar" | "wind";

export interface Site {
  id: string;
  display_name: string;
  country: string;
  region: string;
  cod: string; // Commercial Operation Date (DD/MM/YYYY)
  technology: string;
  site_type: SiteType;
  status: SiteStatus;
  lat: number;
  lon: number;

  // Electrical specs
  cap_ac_kw: number;
  cap_dc_kwp: number;
  n_inverters: number;
  inv_ac_kw: number;
  inv_model: string;
  n_modules: number;
  module_wp: number;
  module_brand: string;
  site_timezone?: string;
  irradiance_basis?: string;
  module_tilt_deg?: number;
  tariff_eur_mwh?: number;
  has_bess?: boolean;
  bess_power_kw?: number;
  bess_energy_kwh?: number;
  bess_manufacturer?: string;
  bess_model?: string;
  bess_chemistry?: string;
  bess_duration_hours?: number;
  bess_roundtrip_efficiency_pct?: number;
  bess_container_count?: number;
  retrofit_bess_enabled?: boolean;
  retrofit_bess_power_kw?: number;
  retrofit_bess_energy_kwh?: number;
  retrofit_bess_cost_eur_kwh?: number;
  retrofit_bess_land_area_m2?: number;
  dc_ac_ratio: number;

  // Analysis parameters
  design_pr: number;
  operating_pr_target: number;
  interval_min: number;
  irr_threshold: number;
  power_threshold: number;
  temp_coeff?: number;

  // Data directory (analysis service)
  data_dir?: string;

  // Ownership
  owner_id?: string;
  plan_type?: "one_shot" | "unlimited";
  hub_height_m?: number;
  tip_height_m?: number;
  rotor_diameter_m?: number;
  expected_aep_gwh?: number;
  solar_module_types?: SolarModuleType[];
  solar_inverter_units?: SolarInverterUnit[];
}

export interface SolarModuleType {
  id: string;
  manufacturer?: string;
  model: string;
  module_wp: number;
  quantity: number;
  technology?: string;
  cell_type?: string;
  module_efficiency_pct?: number;
  bifaciality_pct?: number;
  temp_coeff_pmax_pct_per_c?: number;
  temp_coeff_voc_pct_per_c?: number;
  temp_coeff_isc_pct_per_c?: number;
  first_year_degradation_pct?: number;
  annual_degradation_pct?: number;
  length_mm?: number;
  width_mm?: number;
  thickness_mm?: number;
  weight_kg?: number;
  max_system_voltage_v?: number;
  operating_temp_min_c?: number;
  operating_temp_max_c?: number;
  glass_description?: string;
  frame_description?: string;
  source_url?: string;
}

export interface SolarInverterUnit {
  id?: string;
  tag: string;
  module_count?: number;
  dc_capacity_kwp: number;
  ac_capacity_kw?: number;
}
