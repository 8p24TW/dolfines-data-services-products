export type SiteStatus = "operational" | "maintenance" | "offline";
export type SiteType = "solar" | "wind";

export interface Site {
  id: string;
  display_name: string;
  country: string;
  region: string;
  cod: string;
  technology: string;
  site_type: SiteType;
  status: SiteStatus;
  lat: number;
  lon: number;
  cap_ac_kw: number;
  cap_dc_kwp: number;
  n_inverters: number;
  inv_ac_kw: number;
  inv_model: string;
  n_modules: number;
  module_wp: number;
  module_brand: string;
  dc_ac_ratio: number;
  design_pr: number;
  operating_pr_target: number;
  interval_min: number;
  irr_threshold: number;
  power_threshold: number;
  temp_coeff?: number;
  data_dir?: string;
  owner_id?: string;
  plan_type?: "one_shot" | "unlimited";
}
