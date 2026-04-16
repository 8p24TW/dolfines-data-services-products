import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getCurrentUserRecord } from "@/lib/server/auth";
import { mapSite, parseUiDate } from "@/lib/server/site-mapper";

export const runtime = "nodejs";

async function getAccessibleSite(id: string, userId?: string, organizationId?: string | null) {
  const accessFilters = [];
  if (userId) accessFilters.push({ users: { some: { id: userId } } });
  if (organizationId) accessFilters.push({ organizationId });

  return prisma.site.findFirst({
    where: {
      id,
      ...(accessFilters.length ? { OR: accessFilters } : {}),
    },
    include: { solar_module_types: true, solar_inverter_units: true },
  });
}

export async function GET(_request: Request, context: { params: { id: string } }) {
  try {
    const { user } = await getCurrentUserRecord();
    const site = await getAccessibleSite(context.params.id, user?.id, user?.organizationId);
    if (!site) {
      return NextResponse.json({ error: "Site not found" }, { status: 404 });
    }
    return NextResponse.json(mapSite(site));
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to load site" }, { status: 500 });
  }
}

export async function PUT(request: Request, context: { params: { id: string } }) {
  try {
    const { user } = await getCurrentUserRecord();
    const existing = await getAccessibleSite(context.params.id, user?.id, user?.organizationId);
    if (!existing) {
      return NextResponse.json({ error: "Site not found" }, { status: 404 });
    }

    const body = await request.json();
    const has = (key: string) => Object.prototype.hasOwnProperty.call(body, key);
    const solarModuleTypes = Array.isArray(body.solar_module_types) ? body.solar_module_types : undefined;
    const solarInverterUnits = Array.isArray(body.solar_inverter_units) ? body.solar_inverter_units : undefined;

    const updated = await prisma.site.update({
      where: { id: context.params.id },
      data: {
        ...(has("display_name") ? { display_name: body.display_name } : {}),
        ...(has("country") ? { country: body.country } : {}),
        ...(has("region") ? { region: body.region } : {}),
        ...(has("cod") ? { cod: parseUiDate(body.cod) ?? existing.cod } : {}),
        ...(has("technology") ? { technology: body.technology } : {}),
        ...(has("site_type") ? { site_type: body.site_type } : {}),
        ...(has("status") ? { status: body.status } : {}),
        ...(has("lat") ? { lat: body.lat } : {}),
        ...(has("lon") ? { lon: body.lon } : {}),
        ...(has("cap_ac_kw") ? { cap_ac_kw: body.cap_ac_kw } : {}),
        ...(has("cap_dc_kwp") ? { cap_dc_kwp: body.cap_dc_kwp } : {}),
        ...(has("n_inverters") ? { n_inverters: body.n_inverters } : {}),
        ...(has("inv_ac_kw") ? { inv_ac_kw: body.inv_ac_kw } : {}),
        ...(has("inv_model") ? { inv_model: body.inv_model } : {}),
        ...(has("n_modules") ? { n_modules: body.n_modules } : {}),
        ...(has("module_wp") ? { module_wp: body.module_wp } : {}),
        ...(has("module_brand") ? { module_brand: body.module_brand } : {}),
        ...(has("site_timezone") ? { site_timezone: body.site_timezone } : {}),
        ...(has("irradiance_basis") ? { irradiance_basis: body.irradiance_basis } : {}),
        ...(has("module_tilt_deg") ? { module_tilt_deg: body.module_tilt_deg } : {}),
        ...(has("tariff_eur_mwh") ? { tariff_eur_mwh: body.tariff_eur_mwh } : {}),
        ...(has("has_bess") ? { has_bess: body.has_bess } : {}),
        ...(has("bess_power_kw") ? { bess_power_kw: body.bess_power_kw } : {}),
        ...(has("bess_energy_kwh") ? { bess_energy_kwh: body.bess_energy_kwh } : {}),
        ...(has("bess_manufacturer") ? { bess_manufacturer: body.bess_manufacturer } : {}),
        ...(has("bess_model") ? { bess_model: body.bess_model } : {}),
        ...(has("bess_chemistry") ? { bess_chemistry: body.bess_chemistry } : {}),
        ...(has("bess_duration_hours") ? { bess_duration_hours: body.bess_duration_hours } : {}),
        ...(has("bess_roundtrip_efficiency_pct") ? { bess_roundtrip_efficiency_pct: body.bess_roundtrip_efficiency_pct } : {}),
        ...(has("bess_container_count") ? { bess_container_count: body.bess_container_count } : {}),
        ...(has("retrofit_bess_enabled") ? { retrofit_bess_enabled: body.retrofit_bess_enabled } : {}),
        ...(has("retrofit_bess_power_kw") ? { retrofit_bess_power_kw: body.retrofit_bess_power_kw } : {}),
        ...(has("retrofit_bess_energy_kwh") ? { retrofit_bess_energy_kwh: body.retrofit_bess_energy_kwh } : {}),
        ...(has("retrofit_bess_cost_eur_kwh") ? { retrofit_bess_cost_eur_kwh: body.retrofit_bess_cost_eur_kwh } : {}),
        ...(has("retrofit_bess_land_area_m2") ? { retrofit_bess_land_area_m2: body.retrofit_bess_land_area_m2 } : {}),
        ...(has("dc_ac_ratio") ? { dc_ac_ratio: body.dc_ac_ratio } : {}),
        ...(has("design_pr") ? { design_pr: body.design_pr } : {}),
        ...(has("operating_pr_target") ? { operating_pr_target: body.operating_pr_target } : {}),
        ...(has("interval_min") ? { interval_min: body.interval_min } : {}),
        ...(has("irr_threshold") ? { irr_threshold: body.irr_threshold } : {}),
        ...(has("power_threshold") ? { power_threshold: body.power_threshold } : {}),
        ...(has("temp_coeff") ? { temp_coeff: body.temp_coeff } : {}),
        ...(has("data_dir") ? { data_dir: body.data_dir } : {}),
        ...(has("owner_id") ? { owner_id: body.owner_id } : {}),
        ...(has("plan_type") ? { plan_type: body.plan_type } : {}),
        ...(has("hub_height_m") ? { hub_height_m: body.hub_height_m } : {}),
        ...(has("tip_height_m") ? { tip_height_m: body.tip_height_m } : {}),
        ...(has("rotor_diameter_m") ? { rotor_diameter_m: body.rotor_diameter_m } : {}),
        ...(has("expected_aep_gwh") ? { expected_aep_gwh: body.expected_aep_gwh } : {}),
        ...(solarModuleTypes
          ? {
              solar_module_types: {
                deleteMany: {},
                create: solarModuleTypes.map((moduleType: {
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
                }) => ({
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
              },
            }
          : {}),
        ...(solarInverterUnits
          ? {
              solar_inverter_units: {
                deleteMany: {},
                create: solarInverterUnits.map((inverterUnit: { tag: string; module_count?: number | null; dc_capacity_kwp: number; ac_capacity_kw?: number }) => ({
                  tag: inverterUnit.tag,
                  module_count: inverterUnit.module_count ?? null,
                  dc_capacity_kwp: inverterUnit.dc_capacity_kwp,
                  ac_capacity_kw: inverterUnit.ac_capacity_kw ?? null,
                })),
              },
            }
          : {}),
      },
      include: { solar_module_types: true, solar_inverter_units: true },
    });

    return NextResponse.json(mapSite(updated));
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to update site" }, { status: 500 });
  }
}

export async function DELETE(_request: Request, context: { params: { id: string } }) {
  try {
    const { user } = await getCurrentUserRecord();
    const existing = await getAccessibleSite(context.params.id, user?.id, user?.organizationId);
    if (!existing) {
      return NextResponse.json({ error: "Site not found" }, { status: 404 });
    }

    await prisma.site.delete({ where: { id: context.params.id } });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof Error && error.message === "UNAUTHORIZED") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Failed to delete site" }, { status: 500 });
  }
}
