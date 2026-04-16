import { PrismaClient, type PlanType, type SiteStatus, type SiteType } from "@prisma/client";
import path from "node:path";

const prisma = new PrismaClient();

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const repatRoot = path.join(repoRoot, "REVEAL");
const scadaPvAnalysisRoot = path.join(repatRoot, "SCADA PV Analysis");

type DemoOrganization = {
  id: string;
  name: string;
};

type DemoUser = {
  id: string;
  email: string;
  password: string;
  display_name: string;
  plan_type: PlanType;
  organizationId: string;
  siteIds: string[];
};

type DemoSite = {
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
  module_brand?: string;
  site_timezone?: string;
  irradiance_basis?: string;
  module_tilt_deg?: number;
  tariff_eur_mwh?: number;
  dc_ac_ratio: number;
  design_pr: number;
  operating_pr_target: number;
  interval_min: number;
  irr_threshold: number;
  power_threshold: number;
  data_dir?: string;
  plan_type?: PlanType;
  owner_id?: string;
  hub_height_m?: number;
  tip_height_m?: number;
  rotor_diameter_m?: number;
  expected_aep_gwh?: number;
};

type DemoSolarModuleType = {
  id: string;
  siteId: string;
  manufacturer?: string;
  model: string;
  module_wp: number;
  quantity: number;
};

type DemoSolarInverterUnit = {
  id: string;
  siteId: string;
  tag: string;
  dc_capacity_kwp: number;
  ac_capacity_kw?: number;
};

const organizations: DemoOrganization[] = [
  { id: "org_dolfines_8p2", name: "Dolfines / 8p2 Advisory" },
  { id: "org_solar_co", name: "Solar Co." },
];

const users: DemoUser[] = [
  {
    id: "user_demo_dolfines",
    email: "demo@dolfines.com",
    password: "repat2024",
    display_name: "Demo User",
    plan_type: "unlimited",
    organizationId: "org_dolfines_8p2",
    siteIds: ["SOHMEX", "VENTOUX_PV", "LIMOUSIN_WIND", "NORMANDIE_PV"],
  },
  {
    id: "user_client_solar_co",
    email: "client@solar-co.com",
    password: "solar2024",
    display_name: "Solar Co. Manager",
    plan_type: "unlimited",
    organizationId: "org_solar_co",
    siteIds: ["SOHMEX"],
  },
];

const sites: DemoSite[] = [
  {
    id: "SOHMEX",
    display_name: "SOHMEX Solar Farm",
    country: "France",
    region: "Grand Est",
    cod: "01/06/2022",
    technology: "CdTe (First Solar Series 6)",
    site_type: "solar",
    status: "operational",
    lat: 48.8,
    lon: 6.1,
    cap_ac_kw: 5250.0,
    cap_dc_kwp: 4977.0,
    n_inverters: 21,
    inv_ac_kw: 250.0,
    inv_model: "Sungrow SG250HX",
    n_modules: 10815,
    module_wp: 460.0,
    module_brand: "First Solar",
    site_timezone: "Europe/Paris",
    irradiance_basis: "poa",
    module_tilt_deg: 18,
    tariff_eur_mwh: 68,
    dc_ac_ratio: 0.948,
    design_pr: 0.8,
    operating_pr_target: 0.79,
    interval_min: 10,
    irr_threshold: 50.0,
    power_threshold: 5.0,
    data_dir: path.join(scadaPvAnalysisRoot, "00orig"),
    plan_type: "unlimited",
  },
  {
    id: "VENTOUX_PV",
    display_name: "Ventoux Solaire",
    country: "France",
    region: "Provence-Alpes-Côte d'Azur",
    cod: "15/03/2021",
    technology: "Mono PERC (Jinko Tiger)",
    site_type: "solar",
    status: "operational",
    lat: 44.1,
    lon: 5.3,
    cap_ac_kw: 12000.0,
    cap_dc_kwp: 12480.0,
    n_inverters: 120,
    inv_ac_kw: 100.0,
    inv_model: "Huawei SUN2000-100KTL",
    n_modules: 27200,
    module_wp: 459.0,
    module_brand: "Jinko",
    site_timezone: "Europe/Paris",
    irradiance_basis: "poa",
    module_tilt_deg: 22,
    tariff_eur_mwh: 72,
    dc_ac_ratio: 1.04,
    design_pr: 0.81,
    operating_pr_target: 0.8,
    interval_min: 15,
    irr_threshold: 50.0,
    power_threshold: 5.0,
    data_dir: "",
    plan_type: "unlimited",
  },
  {
    id: "LIMOUSIN_WIND",
    display_name: "Parc Éolien du Limousin",
    country: "France",
    region: "Nouvelle-Aquitaine",
    cod: "01/11/2019",
    technology: "Vestas V136-4.5 MW",
    site_type: "wind",
    status: "maintenance",
    lat: 45.8,
    lon: 1.9,
    cap_ac_kw: 18000.0,
    cap_dc_kwp: 18000.0,
    n_inverters: 4,
    inv_ac_kw: 4500.0,
    inv_model: "—",
    n_modules: 0,
    module_wp: 0.0,
    site_timezone: "Europe/Paris",
    tariff_eur_mwh: 94,
    dc_ac_ratio: 1.0,
    design_pr: 0.94,
    operating_pr_target: 0.92,
    interval_min: 10,
    irr_threshold: 0.0,
    power_threshold: 10.0,
    data_dir: "",
    plan_type: "unlimited",
    hub_height_m: 112,
    tip_height_m: 180,
    rotor_diameter_m: 136,
    expected_aep_gwh: 52.4,
  },
  {
    id: "NORMANDIE_PV",
    display_name: "Normandie Agri-PV",
    country: "France",
    region: "Normandie",
    cod: "20/07/2023",
    technology: "Bifacial (LONGi Hi-MO 6)",
    site_type: "solar",
    status: "operational",
    lat: 49.2,
    lon: 0.4,
    cap_ac_kw: 7500.0,
    cap_dc_kwp: 7560.0,
    n_inverters: 50,
    inv_ac_kw: 150.0,
    inv_model: "SMA Sunny Tripower CORE2",
    n_modules: 16000,
    module_wp: 472.5,
    module_brand: "LONGi",
    site_timezone: "Europe/Paris",
    irradiance_basis: "poa",
    module_tilt_deg: 15,
    tariff_eur_mwh: 74,
    dc_ac_ratio: 1.01,
    design_pr: 0.79,
    operating_pr_target: 0.78,
    interval_min: 15,
    irr_threshold: 50.0,
    power_threshold: 5.0,
    data_dir: "",
    plan_type: "unlimited",
  },
];

const solarModuleTypes: DemoSolarModuleType[] = [
  {
    id: "module_sohmex_primary",
    siteId: "SOHMEX",
    manufacturer: "First Solar",
    model: "CdTe (First Solar Series 6)",
    module_wp: 460.0,
    quantity: 10815,
  },
  {
    id: "module_ventoux_primary",
    siteId: "VENTOUX_PV",
    manufacturer: "Jinko",
    model: "Mono PERC (Jinko Tiger)",
    module_wp: 459.0,
    quantity: 27200,
  },
  {
    id: "module_normandie_primary",
    siteId: "NORMANDIE_PV",
    manufacturer: "LONGi",
    model: "Bifacial (LONGi Hi-MO 6)",
    module_wp: 472.5,
    quantity: 16000,
  },
];

const solarInverterUnits: DemoSolarInverterUnit[] = [
  ...Array.from({ length: 21 }, (_, index) => ({
    id: `inverter_sohmex_${index + 1}`,
    siteId: "SOHMEX",
    tag: `OND${Math.floor(index / 15) + 1}.${(index % 15) + 1}`,
    dc_capacity_kwp: 4977.0 / 21,
    ac_capacity_kw: 250.0,
  })),
  ...Array.from({ length: 120 }, (_, index) => ({
    id: `inverter_ventoux_${index + 1}`,
    siteId: "VENTOUX_PV",
    tag: `INV${index + 1}`,
    dc_capacity_kwp: 12480.0 / 120,
    ac_capacity_kw: 100.0,
  })),
  ...Array.from({ length: 50 }, (_, index) => ({
    id: `inverter_normandie_${index + 1}`,
    siteId: "NORMANDIE_PV",
    tag: `INV${index + 1}`,
    dc_capacity_kwp: 7560.0 / 50,
    ac_capacity_kw: 150.0,
  })),
];

function parseFrenchDate(value: string): Date {
  const [day, month, year] = value.split("/");
  return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
}

async function main() {
  const demoSiteIds = sites.map((site) => site.id);
  const demoUserIds = users.map((user) => user.id);
  const demoOrganizationIds = organizations.map((organization) => organization.id);
  const demoOrganizationNames = organizations.map((organization) => organization.name);

  await prisma.reportJob.deleteMany({
    where: { siteId: { in: demoSiteIds } },
  });
  await prisma.report.deleteMany({
    where: { siteId: { in: demoSiteIds } },
  });
  await prisma.solarInverterUnit.deleteMany({
    where: { siteId: { in: demoSiteIds } },
  });
  await prisma.solarModuleType.deleteMany({
    where: { siteId: { in: demoSiteIds } },
  });

  // Preserve real production users and sites; seed should only refresh demo content.
  await prisma.site.deleteMany({
    where: { id: { in: demoSiteIds } },
  });
  await prisma.user.deleteMany({
    where: { id: { in: demoUserIds } },
  });
  await prisma.organization.deleteMany({
    where: {
      OR: [
        { id: { in: demoOrganizationIds } },
        { name: { in: demoOrganizationNames } },
      ],
    },
  });

  for (const organization of organizations) {
    await prisma.organization.upsert({
      where: { name: organization.name },
      update: {},
      create: organization,
    });
  }

  for (const user of users) {
    await prisma.user.upsert({
      where: { email: user.email },
      update: {
        password: user.password,
        display_name: user.display_name,
        plan_type: user.plan_type,
        organizationId: user.organizationId,
      },
      create: {
        id: user.id,
        email: user.email,
        password: user.password,
        display_name: user.display_name,
        plan_type: user.plan_type,
        organizationId: user.organizationId,
      }
    });
  }

  for (const site of sites) {
    const userConnections = users
      .filter((user) => user.siteIds.includes(site.id))
      .map((user) => ({ id: user.id }));

    await prisma.site.upsert({
      where: { id: site.id },
      update: {
        display_name: site.display_name,
        country: site.country,
        region: site.region,
        cod: parseFrenchDate(site.cod),
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
        module_brand: site.module_brand ?? null,
        site_timezone: site.site_timezone ?? "Europe/Paris",
        irradiance_basis: site.irradiance_basis ?? null,
        module_tilt_deg: site.module_tilt_deg ?? null,
        tariff_eur_mwh: site.tariff_eur_mwh ?? null,
        dc_ac_ratio: site.dc_ac_ratio,
        design_pr: site.design_pr,
        operating_pr_target: site.operating_pr_target,
        interval_min: site.interval_min,
        irr_threshold: site.irr_threshold,
        power_threshold: site.power_threshold,
        data_dir: site.data_dir || null,
        owner_id: site.owner_id ?? null,
        plan_type: site.plan_type ?? null,
        hub_height_m: site.hub_height_m ?? null,
        tip_height_m: site.tip_height_m ?? null,
        rotor_diameter_m: site.rotor_diameter_m ?? null,
        expected_aep_gwh: site.expected_aep_gwh ?? null,
        users: {
          set: userConnections,
        },
      },
      create: {
        id: site.id,
        display_name: site.display_name,
        country: site.country,
        region: site.region,
        cod: parseFrenchDate(site.cod),
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
        module_brand: site.module_brand ?? null,
        site_timezone: site.site_timezone ?? "Europe/Paris",
        irradiance_basis: site.irradiance_basis ?? null,
        module_tilt_deg: site.module_tilt_deg ?? null,
        tariff_eur_mwh: site.tariff_eur_mwh ?? null,
        dc_ac_ratio: site.dc_ac_ratio,
        design_pr: site.design_pr,
        operating_pr_target: site.operating_pr_target,
        interval_min: site.interval_min,
        irr_threshold: site.irr_threshold,
        power_threshold: site.power_threshold,
        data_dir: site.data_dir || null,
        owner_id: site.owner_id ?? null,
        plan_type: site.plan_type ?? null,
        hub_height_m: site.hub_height_m ?? null,
        tip_height_m: site.tip_height_m ?? null,
        rotor_diameter_m: site.rotor_diameter_m ?? null,
        expected_aep_gwh: site.expected_aep_gwh ?? null,
        users: {
          connect: userConnections,
        },
      }
    });
  }

  for (const moduleType of solarModuleTypes) {
    await prisma.solarModuleType.create({
      data: moduleType,
    });
  }

  for (const inverterUnit of solarInverterUnits) {
    await prisma.solarInverterUnit.create({
      data: inverterUnit,
    });
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
