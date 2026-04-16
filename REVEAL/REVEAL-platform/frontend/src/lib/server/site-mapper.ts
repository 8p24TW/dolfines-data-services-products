import type {
  Prisma,
  Report as PrismaReport,
  ReportJob as PrismaReportJob,
  Site as PrismaSite,
  SolarInverterUnit as PrismaSolarInverterUnit,
  SolarModuleType as PrismaSolarModuleType,
} from "@prisma/client";
import crypto from "node:crypto";
import type { ReportJob, ReportMeta } from "@/types/report";
import type { Site, SolarInverterUnit, SolarModuleType } from "@/types/site";

type SiteModuleRecord = PrismaSolarModuleType & {
  technology?: string | null;
  cell_type?: string | null;
  module_efficiency_pct?: number | null;
  bifaciality_pct?: number | null;
  temp_coeff_pmax_pct_per_c?: number | null;
  temp_coeff_voc_pct_per_c?: number | null;
  temp_coeff_isc_pct_per_c?: number | null;
  first_year_degradation_pct?: number | null;
  annual_degradation_pct?: number | null;
  length_mm?: number | null;
  width_mm?: number | null;
  thickness_mm?: number | null;
  weight_kg?: number | null;
  max_system_voltage_v?: number | null;
  operating_temp_min_c?: number | null;
  operating_temp_max_c?: number | null;
  glass_description?: string | null;
  frame_description?: string | null;
  source_url?: string | null;
};

type SiteWithModules = PrismaSite & {
  has_bess?: boolean;
  bess_power_kw?: number | null;
  bess_energy_kwh?: number | null;
  bess_manufacturer?: string | null;
  bess_model?: string | null;
  bess_chemistry?: string | null;
  bess_duration_hours?: number | null;
  bess_roundtrip_efficiency_pct?: number | null;
  bess_container_count?: number | null;
  retrofit_bess_enabled?: boolean | null;
  retrofit_bess_power_kw?: number | null;
  retrofit_bess_energy_kwh?: number | null;
  retrofit_bess_cost_eur_kwh?: number | null;
  retrofit_bess_land_area_m2?: number | null;
  solar_module_types?: SiteModuleRecord[];
  solar_inverter_units?: PrismaSolarInverterUnit[];
};

export function formatDateForUi(date: Date | null | undefined) {
  if (!date) return "";
  const day = `${date.getUTCDate()}`.padStart(2, "0");
  const month = `${date.getUTCMonth() + 1}`.padStart(2, "0");
  const year = `${date.getUTCFullYear()}`;
  return `${day}/${month}/${year}`;
}

export function formatDateIso(date: Date | null | undefined) {
  if (!date) return undefined;
  return date.toISOString().slice(0, 10);
}

export function parseUiDate(value: string | null | undefined) {
  if (!value) return null;
  const [day, month, year] = value.split("/");
  if (!day || !month || !year) return null;
  return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
}

export function mapSolarModuleType(moduleType: SiteModuleRecord): SolarModuleType {
  return {
    id: moduleType.id,
    manufacturer: moduleType.manufacturer ?? undefined,
    model: moduleType.model,
    module_wp: moduleType.module_wp,
    quantity: moduleType.quantity,
    technology: moduleType.technology ?? undefined,
    cell_type: moduleType.cell_type ?? undefined,
    module_efficiency_pct: moduleType.module_efficiency_pct ?? undefined,
    bifaciality_pct: moduleType.bifaciality_pct ?? undefined,
    temp_coeff_pmax_pct_per_c: moduleType.temp_coeff_pmax_pct_per_c ?? undefined,
    temp_coeff_voc_pct_per_c: moduleType.temp_coeff_voc_pct_per_c ?? undefined,
    temp_coeff_isc_pct_per_c: moduleType.temp_coeff_isc_pct_per_c ?? undefined,
    first_year_degradation_pct: moduleType.first_year_degradation_pct ?? undefined,
    annual_degradation_pct: moduleType.annual_degradation_pct ?? undefined,
    length_mm: moduleType.length_mm ?? undefined,
    width_mm: moduleType.width_mm ?? undefined,
    thickness_mm: moduleType.thickness_mm ?? undefined,
    weight_kg: moduleType.weight_kg ?? undefined,
    max_system_voltage_v: moduleType.max_system_voltage_v ?? undefined,
    operating_temp_min_c: moduleType.operating_temp_min_c ?? undefined,
    operating_temp_max_c: moduleType.operating_temp_max_c ?? undefined,
    glass_description: moduleType.glass_description ?? undefined,
    frame_description: moduleType.frame_description ?? undefined,
    source_url: moduleType.source_url ?? undefined,
  };
}

export function mapSolarInverterUnit(inverterUnit: PrismaSolarInverterUnit): SolarInverterUnit {
  return {
    id: inverterUnit.id,
    tag: inverterUnit.tag,
    module_count: inverterUnit.module_count ?? undefined,
    dc_capacity_kwp: inverterUnit.dc_capacity_kwp,
    ac_capacity_kw: inverterUnit.ac_capacity_kw ?? undefined,
  };
}

export function mapSite(site: SiteWithModules): Site {
  return {
    id: site.id,
    display_name: site.display_name,
    country: site.country,
    region: site.region,
    cod: formatDateForUi(site.cod),
    technology: site.technology,
    site_type: site.site_type,
    status: site.status,
    lat: site.lat,
    lon: site.lon,
    cap_ac_kw: site.cap_ac_kw,
    cap_dc_kwp: site.cap_dc_kwp,
    n_inverters: site.n_inverters,
    inv_ac_kw: site.inv_ac_kw,
    inv_model: site.inv_model,
    n_modules: site.n_modules,
    module_wp: site.module_wp,
    module_brand: site.module_brand ?? "",
    site_timezone: site.site_timezone ?? undefined,
    irradiance_basis: site.irradiance_basis ?? undefined,
    module_tilt_deg: site.module_tilt_deg ?? undefined,
    tariff_eur_mwh: site.tariff_eur_mwh ?? undefined,
    has_bess: site.has_bess,
    bess_power_kw: site.bess_power_kw ?? undefined,
    bess_energy_kwh: site.bess_energy_kwh ?? undefined,
    bess_manufacturer: site.bess_manufacturer ?? undefined,
    bess_model: site.bess_model ?? undefined,
    bess_chemistry: site.bess_chemistry ?? undefined,
    bess_duration_hours: site.bess_duration_hours ?? undefined,
    bess_roundtrip_efficiency_pct: site.bess_roundtrip_efficiency_pct ?? undefined,
    bess_container_count: site.bess_container_count ?? undefined,
    retrofit_bess_enabled: site.retrofit_bess_enabled ?? undefined,
    retrofit_bess_power_kw: site.retrofit_bess_power_kw ?? undefined,
    retrofit_bess_energy_kwh: site.retrofit_bess_energy_kwh ?? undefined,
    retrofit_bess_cost_eur_kwh: site.retrofit_bess_cost_eur_kwh ?? undefined,
    retrofit_bess_land_area_m2: site.retrofit_bess_land_area_m2 ?? undefined,
    dc_ac_ratio: site.dc_ac_ratio,
    design_pr: site.design_pr,
    operating_pr_target: site.operating_pr_target,
    interval_min: site.interval_min,
    irr_threshold: site.irr_threshold,
    power_threshold: site.power_threshold,
    temp_coeff: site.temp_coeff ?? undefined,
    data_dir: site.data_dir ?? undefined,
    owner_id: site.owner_id ?? undefined,
    plan_type: site.plan_type ?? undefined,
    hub_height_m: site.hub_height_m ?? undefined,
    tip_height_m: site.tip_height_m ?? undefined,
    rotor_diameter_m: site.rotor_diameter_m ?? undefined,
    expected_aep_gwh: site.expected_aep_gwh ?? undefined,
    solar_module_types: site.solar_module_types?.map(mapSolarModuleType),
    solar_inverter_units: site.solar_inverter_units?.map(mapSolarInverterUnit),
  };
}

export function mapReport(report: PrismaReport): ReportMeta {
  return {
    id: report.id,
    siteId: report.siteId,
    reportType: report.reportType,
    reportDate: formatDateIso(report.reportDate),
    generatedAt: report.generatedAt.toISOString(),
    lang: report.lang,
    filename: report.filename,
    downloadUrl: report.downloadUrl,
    sizeBytes: report.sizeBytes ?? undefined,
  };
}

export function mapReportJob(job: PrismaReportJob): ReportJob {
  return {
    jobId: job.id,
    siteId: job.siteId,
    status: job.status,
    progress: job.progress,
    pdfUrl: job.pdfUrl ?? undefined,
    error: job.error ?? undefined,
    reportType: job.reportType,
    reportDate: formatDateIso(job.reportDate),
    lang: job.lang,
  };
}

export function mapSiteToAnalysisConfig(site: Site) {
  return {
    ...site,
    solar_module_types: site.solar_module_types?.map((moduleType) => ({
      ...moduleType,
    })),
  };
}

export function buildSiteCreateInput(
  site: Partial<Site>,
  extras: { ownerId?: string | null; organizationId?: string | null }
): Prisma.SiteCreateInput {
  return {
    id: site.id ?? crypto.randomUUID(),
    display_name: site.display_name ?? "New Site",
    country: site.country ?? "",
    region: site.region ?? "",
    cod: parseUiDate(site.cod) ?? new Date(),
    technology: site.technology ?? "",
    site_type: site.site_type ?? "solar",
    status: site.status ?? "operational",
    lat: site.lat ?? 0,
    lon: site.lon ?? 0,
    cap_ac_kw: site.cap_ac_kw ?? 0,
    cap_dc_kwp: site.cap_dc_kwp ?? 0,
    n_inverters: site.n_inverters ?? 0,
    inv_ac_kw: site.inv_ac_kw ?? 0,
    inv_model: site.inv_model ?? "",
    n_modules: site.n_modules ?? 0,
    module_wp: site.module_wp ?? 0,
    module_brand: site.module_brand ?? null,
    site_timezone: site.site_timezone ?? "Europe/Paris",
    irradiance_basis: site.irradiance_basis ?? null,
    module_tilt_deg: site.module_tilt_deg ?? null,
    tariff_eur_mwh: site.tariff_eur_mwh ?? null,
    has_bess: site.has_bess ?? false,
    bess_power_kw: site.bess_power_kw ?? null,
    bess_energy_kwh: site.bess_energy_kwh ?? null,
    bess_manufacturer: site.bess_manufacturer ?? null,
    bess_model: site.bess_model ?? null,
    bess_chemistry: site.bess_chemistry ?? null,
    bess_duration_hours: site.bess_duration_hours ?? null,
    bess_roundtrip_efficiency_pct: site.bess_roundtrip_efficiency_pct ?? null,
    bess_container_count: site.bess_container_count ?? null,
    retrofit_bess_enabled: site.retrofit_bess_enabled ?? false,
    retrofit_bess_power_kw: site.retrofit_bess_power_kw ?? null,
    retrofit_bess_energy_kwh: site.retrofit_bess_energy_kwh ?? null,
    retrofit_bess_cost_eur_kwh: site.retrofit_bess_cost_eur_kwh ?? null,
    retrofit_bess_land_area_m2: site.retrofit_bess_land_area_m2 ?? null,
    dc_ac_ratio: site.dc_ac_ratio ?? 1,
    design_pr: site.design_pr ?? 0,
    operating_pr_target: site.operating_pr_target ?? site.design_pr ?? 0,
    interval_min: site.interval_min ?? 15,
    irr_threshold: site.irr_threshold ?? 0,
    power_threshold: site.power_threshold ?? 0,
    temp_coeff: site.temp_coeff ?? null,
    data_dir: site.data_dir ?? null,
    owner_id: extras.ownerId ?? site.owner_id ?? null,
    plan_type: site.plan_type ?? null,
    hub_height_m: site.hub_height_m ?? null,
    tip_height_m: site.tip_height_m ?? null,
    rotor_diameter_m: site.rotor_diameter_m ?? null,
    expected_aep_gwh: site.expected_aep_gwh ?? null,
    organization: extras.organizationId
      ? { connect: { id: extras.organizationId } }
      : undefined,
    users: extras.ownerId
      ? { connect: [{ id: extras.ownerId }] }
      : undefined,
    solar_module_types: site.solar_module_types?.length
      ? {
          create: site.solar_module_types.map((moduleType) => ({
            manufacturer: moduleType.manufacturer ?? null,
            model: moduleType.model,
            module_wp: moduleType.module_wp,
            quantity: moduleType.quantity,
            technology: moduleType.technology ?? null,
            cell_type: moduleType.cell_type ?? null,
            module_efficiency_pct: moduleType.module_efficiency_pct ?? null,
            bifaciality_pct: moduleType.bifaciality_pct ?? null,
            temp_coeff_pmax_pct_per_c: moduleType.temp_coeff_pmax_pct_per_c ?? null,
            temp_coeff_voc_pct_per_c: moduleType.temp_coeff_voc_pct_per_c ?? null,
            temp_coeff_isc_pct_per_c: moduleType.temp_coeff_isc_pct_per_c ?? null,
            first_year_degradation_pct: moduleType.first_year_degradation_pct ?? null,
            annual_degradation_pct: moduleType.annual_degradation_pct ?? null,
            length_mm: moduleType.length_mm ?? null,
            width_mm: moduleType.width_mm ?? null,
            thickness_mm: moduleType.thickness_mm ?? null,
            weight_kg: moduleType.weight_kg ?? null,
            max_system_voltage_v: moduleType.max_system_voltage_v ?? null,
            operating_temp_min_c: moduleType.operating_temp_min_c ?? null,
            operating_temp_max_c: moduleType.operating_temp_max_c ?? null,
            glass_description: moduleType.glass_description ?? null,
            frame_description: moduleType.frame_description ?? null,
            source_url: moduleType.source_url ?? null,
          })),
        }
      : undefined,
    solar_inverter_units: site.solar_inverter_units?.length
      ? {
          create: site.solar_inverter_units.map((inverterUnit) => ({
            tag: inverterUnit.tag,
            module_count: inverterUnit.module_count ?? null,
            dc_capacity_kwp: inverterUnit.dc_capacity_kwp,
            ac_capacity_kw: inverterUnit.ac_capacity_kw ?? null,
          })),
        }
      : undefined,
  } as Prisma.SiteCreateInput;
}
