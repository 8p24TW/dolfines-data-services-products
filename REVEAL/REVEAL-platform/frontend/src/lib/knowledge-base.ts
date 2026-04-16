import {
  getBessManufacturers,
  getBessModels,
  getBessSpec,
  getSolarInverterManufacturers,
  getSolarInverterModels,
  getSolarInverterSpec,
  getSolarModuleManufacturers,
  getSolarModuleModels,
  getSolarModuleSpec,
  getWindManufacturers,
  getWindModels,
  getWindSpec,
} from "@/lib/equipment-kb";

export type EquipmentCategory = "inverter" | "module" | "turbine" | "bess";
export type IssueSeverity = "High" | "Medium" | "Info";

export interface EquipmentIssue {
  title: string;
  severity: IssueSeverity;
  summary: string;
  lookOutFor: string[];
}

export interface CompanyProfile {
  name: string;
  founded: string;
  headquarters: string;
  statLabel: string;
  statValue: string;
  overview: string;
  website: string;
  accent: string;
}

export interface ModelKnowledge {
  model: string;
  specs: string[];
  monitoringFocus: string[];
  issues: EquipmentIssue[];
}

export interface ManufacturerKnowledge {
  manufacturer: string;
  company: CompanyProfile;
  models: ModelKnowledge[];
}

export interface CategoryKnowledge {
  key: EquipmentCategory;
  label: {
    en: string;
    fr: string;
  };
  description: {
    en: string;
    fr: string;
  };
  manufacturers: ManufacturerKnowledge[];
}

function specLabel(category: EquipmentCategory, manufacturer: string, model: string) {
  if (category === "inverter") {
    const spec = getSolarInverterSpec(manufacturer, model);
    return spec
      ? [
          `${spec.ac_kw} kW AC`,
          spec.max_efficiency_pct != null ? `${spec.max_efficiency_pct}% max efficiency` : "Max efficiency N/A",
          spec.european_efficiency_pct != null ? `${spec.european_efficiency_pct}% EU efficiency` : "EU efficiency N/A",
          spec.mppt_count != null ? `${spec.mppt_count} MPPT` : "MPPT count N/A",
          spec.max_dc_voltage_v != null ? `${spec.max_dc_voltage_v} V max DC` : "DC voltage class N/A",
          spec.protection_rating ?? "Protection rating N/A",
        ]
      : ["Inverter data unavailable"];
  }

  if (category === "module") {
    const spec = getSolarModuleSpec(manufacturer, model);
    return spec
      ? [
          `${spec.power_wp} Wp`,
          spec.module_efficiency_pct != null ? `${spec.module_efficiency_pct}% efficiency` : "Efficiency N/A",
          spec.cell_type ?? spec.technology,
          spec.bifaciality_pct != null ? `${spec.bifaciality_pct}% bifaciality` : "Monofacial / bifaciality N/A",
          spec.length_mm != null && spec.width_mm != null
            ? `${spec.length_mm} x ${spec.width_mm} mm`
            : "Dimensions N/A",
          spec.weight_kg != null ? `${spec.weight_kg} kg` : "Weight N/A",
          spec.first_year_degradation_pct != null ? `${spec.first_year_degradation_pct}% first-year degradation` : "First-year degradation N/A",
          spec.annual_degradation_pct != null ? `${spec.annual_degradation_pct}% annual degradation` : "Annual degradation N/A",
          spec.max_system_voltage_v != null ? `${spec.max_system_voltage_v} V max system` : "System voltage N/A",
        ]
      : ["PV module data unavailable"];
  }

  if (category === "bess") {
    const spec = getBessSpec(manufacturer, model);
    return spec
      ? [
          `${spec.power_mw} MW power`,
          `${spec.energy_mwh} MWh energy`,
          `${spec.duration_hours} h duration`,
          spec.battery_containers_20ft != null ? `${spec.battery_containers_20ft} x 20 ft battery containers` : "Battery container count N/A",
          spec.pcs_transformer_skids_40ft != null ? `${spec.pcs_transformer_skids_40ft} x 40 ft PCS/transformer skids` : "PCS/transformer skid count N/A",
          spec.cost_eur_kwh != null ? `EUR ${spec.cost_eur_kwh}/kWh placeholder capex` : "Capex placeholder N/A",
          spec.area_with_access_m2 != null ? `${spec.area_with_access_m2} m2 indicative installed area` : "Installed area N/A",
          spec.chemistry ?? "Grid-scale battery chemistry",
          spec.round_trip_efficiency_pct != null ? `${spec.round_trip_efficiency_pct}% AC round-trip efficiency` : "Round-trip efficiency N/A",
          spec.cooling ?? "Cooling N/A",
        ]
      : ["BESS data unavailable"];
  }

  const spec = getWindSpec(manufacturer, model);
  return spec
    ? [
        `${spec.rated_mw} MW rated`,
        `${spec.rotor_diameter_m} m rotor`,
        spec.swept_area_m2 != null ? `${spec.swept_area_m2.toLocaleString()} m2 swept area` : "Swept area N/A",
        spec.hub_height_range_m ? `${spec.hub_height_range_m} m hub-height range` : "Hub-height range N/A",
        spec.iec_class ?? "IEC class N/A",
      ]
    : ["Wind turbine data unavailable"];
}

function getCatalogModels(category: EquipmentCategory, manufacturer: string) {
  if (category === "module") return getSolarModuleModels(manufacturer);
  if (category === "turbine") return getWindModels(manufacturer);
  if (category === "bess") return getBessModels(manufacturer);
  return getSolarInverterModels(manufacturer);
}

function synchronizeKnowledgeModels(base: ManufacturerKnowledge[], category: EquipmentCategory) {
  return base.map((item) => {
    const catalogModels = getCatalogModels(category, item.manufacturer);
    const fallbackFocus = item.models[0]?.monitoringFocus ?? ["Availability trend", "Alarm recurrence", "Performance drift"];
    const fallbackIssues = item.models[0]?.issues ?? [
      {
        title: "Performance deviation review",
        severity: "Medium" as const,
        summary: "REVEAL should compare field performance against the expected datasheet and operating envelope for this equipment family.",
        lookOutFor: ["Availability loss", "Thermal alarms", "Output divergence"],
      },
    ];

    const existing = item.models.filter((model) => catalogModels.includes(model.model));
    const missing = catalogModels
      .filter((model) => !existing.some((entry) => entry.model === model))
      .map((model) => ({
        model,
        specs: specLabel(category, item.manufacturer, model),
        monitoringFocus: [...fallbackFocus],
        issues: fallbackIssues.map((issue) => ({
          ...issue,
          lookOutFor: [...issue.lookOutFor],
        })),
      }));

    return {
      ...item,
      models: [...existing, ...missing],
    };
  });
}

function logoUrl(website: string) {
  return `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(website)}`;
}

const inverterManufacturers = getSolarInverterManufacturers() as string[];
const moduleManufacturers = getSolarModuleManufacturers() as string[];
const windManufacturers = getWindManufacturers() as string[];
const bessManufacturers = getBessManufacturers() as string[];

const inverterKnowledge: ManufacturerKnowledge[] = [
  {
    manufacturer: "Sungrow",
    company: {
      name: "Sungrow",
      founded: "1997",
      headquarters: "Hefei, China",
      statLabel: "Global installed base",
      statValue: "340 GW+ installed worldwide",
      overview:
        "Sungrow is one of the largest utility-scale inverter suppliers globally, with strong coverage across central and string inverter platforms.",
      website: "https://www.sungrowpower.com",
      accent: "from-[#f26f21] via-[#f58d3b] to-[#f8b35d]",
    },
    models: [
      {
        model: "SG250HX",
        specs: specLabel("inverter", "Sungrow", "SG250HX"),
        monitoringFocus: ["Insulation alarms", "Grid overvoltage", "Fan health"],
        issues: [
          {
            title: "DC insulation faults after rain",
            severity: "High",
            summary: "The existing REVEAL fault base flags insulation-related trips as one of the first checks on Sungrow fleets.",
            lookOutFor: ["Wet-weather trips", "Low Riso", "Same MPPT repeatedly alarming"],
          },
          {
            title: "Grid overvoltage at peak export",
            severity: "Medium",
            summary: "Transformer taps or reactive power settings can create short but frequent midday outages.",
            lookOutFor: ["Clear-sky trips", "Voltage alarms", "High stop/start counts"],
          },
          {
            title: "Summer thermal derating",
            severity: "Medium",
            summary: "Fan wear, dust, or direct solar loading can flatten production in hot hours.",
            lookOutFor: ["Fan faults", "Cabinet overheating", "Output lagging peer units"],
          },
        ],
      },
      {
        model: "SG3125HV-MV",
        specs: specLabel("inverter", "Sungrow", "SG3125HV-MV"),
        monitoringFocus: ["Contactor counts", "Cooling auxiliaries", "Transformer-side voltage quality"],
        issues: [
          {
            title: "AC relay or contactor wear",
            severity: "High",
            summary: "High trip-count sites can age switching hardware quickly on central stations.",
            lookOutFor: ["Failed reconnects", "Relay faults", "One skid lagging fleet availability"],
          },
          {
            title: "Thermal management drift",
            severity: "Medium",
            summary: "Central enclosures need disciplined cooling maintenance to avoid lost summer yield.",
            lookOutFor: ["Overtemperature alarms", "Cooling faults", "Midday capping"],
          },
          {
            title: "Cold-morning DC overvoltage risk",
            severity: "Info",
            summary: "String design assumptions should be checked if startup issues only appear in low-temperature conditions.",
            lookOutFor: ["Sunrise startup faults", "Winter-only alarms", "As-built string mismatch"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Huawei",
    company: {
      name: "Huawei FusionSolar",
      founded: "1987",
      headquarters: "Shenzhen, China",
      statLabel: "Platform strength",
      statValue: "Global digital energy and smart PV platform",
      overview:
        "Huawei’s FusionSolar platform is widely used on utility and C&I assets, especially where owners value strong monitoring and gateway integration.",
      website: "https://fusionsolar.huawei.com",
      accent: "from-[#cc1f2f] via-[#df4150] to-[#f27c69]",
    },
    models: [
      {
        model: "SUN2000-100KTL-M1",
        specs: specLabel("inverter", "Huawei", "SUN2000-100KTL-M1"),
        monitoringFocus: ["Insulation alarms", "AFCI events", "SmartLogger uptime"],
        issues: [
          {
            title: "Sensitive insulation-fault detection",
            severity: "High",
            summary: "Huawei fleets often expose moisture or connector issues quickly, which is operationally useful but can create repeated trips if fixes lag.",
            lookOutFor: ["Rain-linked alarms", "Low insulation resistance", "The same input repeatedly tripping"],
          },
          {
            title: "Arc-fault detection events",
            severity: "High",
            summary: "Any AFCI event should trigger a serious connector and cable-route review rather than simple alarm suppression.",
            lookOutFor: ["Arc alarms", "Carbon tracking", "Cable abrasion"],
          },
          {
            title: "Gateway or optimizer comms gaps",
            severity: "Medium",
            summary: "SmartLogger or optimizer comms issues can hide the true production picture and create false performance questions.",
            lookOutFor: ["Plant-wide data gaps", "Offline optimizers", "Status restored after gateway restart"],
          },
        ],
      },
      {
        model: "SUN2000-330KTL-H1",
        specs: specLabel("inverter", "Huawei", "SUN2000-330KTL-H1"),
        monitoringFocus: ["MPPT-level insulation events", "Thermal derating", "Export-period voltage alarms"],
        issues: [
          {
            title: "Insulation issues at scale",
            severity: "High",
            summary: "Large string counts make connector QA and wet-weather diagnostics particularly important.",
            lookOutFor: ["Repeated MPPT faults", "Low Riso", "Fault clusters by array block"],
          },
          {
            title: "Thermal throttling",
            severity: "Medium",
            summary: "Dirty fins, poor shading, or blocked airflow can cause meaningful afternoon derating.",
            lookOutFor: ["Derating status", "Temperature alarms", "Summer-only underperformance"],
          },
          {
            title: "Grid-support tuning issues",
            severity: "Medium",
            summary: "Reactive power and transformer settings need to be checked on export-constrained connections.",
            lookOutFor: ["AC voltage alarms", "Peak-export trips", "Frequent synchronized events"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "SMA",
    company: {
      name: "SMA Solar",
      founded: "1981",
      headquarters: "Niestetal, Germany",
      statLabel: "Positioning",
      statValue: "Long-established utility and C&I inverter supplier",
      overview:
        "SMA remains a benchmark brand in solar power electronics, especially where clients value proven protection behaviour and mature monitoring tools.",
      website: "https://www.sma.de",
      accent: "from-[#f58220] via-[#f7a544] to-[#f9c56e]",
    },
    models: [
      {
        model: "Sunny Tripower CORE2 110",
        specs: specLabel("inverter", "SMA", "Sunny Tripower CORE2 110"),
        monitoringFocus: ["ISOLAN alarms", "AFCI events", "Grid trip rate"],
        issues: [
          {
            title: "Sensitive insulation monitoring",
            severity: "High",
            summary: "SMA’s insulation monitoring can be more conservative than some peers, so wet-weather faults deserve structured follow-up.",
            lookOutFor: ["ISOLAN alarms", "Trips after rain", "One MPPT recurring in logs"],
          },
          {
            title: "AFCI nuisance trips",
            severity: "Medium",
            summary: "Long cable runs and connector quality issues can trigger arc-related events or false positives.",
            lookOutFor: ["Arc warnings", "Repeated events on same strings", "No visible burn damage on first inspection"],
          },
          {
            title: "Strict grid thresholds",
            severity: "Medium",
            summary: "Poor voltage quality tends to show up quickly on SMA fleets and may need transformer or DSO coordination.",
            lookOutFor: ["Peak-export outages", "Voltage alarms", "Site-wide short stops"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "ABB / FIMER",
    company: {
      name: "FIMER",
      founded: "1942",
      headquarters: "Vimercate, Italy",
      statLabel: "Positioning",
      statValue: "Established inverter and power-electronics supplier",
      overview:
        "ABB legacy fleets and newer FIMER-branded units remain common across European portfolios, especially on assets with long operating histories.",
      website: "https://www.fimer.com",
      accent: "from-[#c4151c] via-[#d74349] to-[#e97f82]",
    },
    models: [
      {
        model: "PVS-250-TL",
        specs: specLabel("inverter", "ABB / FIMER", "PVS-250-TL"),
        monitoringFocus: ["Ground-fault history", "Thermal behaviour", "Grid-voltage alarms"],
        issues: [
          {
            title: "Ground-fault and latching trips",
            severity: "High",
            summary: "String-side insulation degradation and wet junction boxes can drive outages that need field reset and root-cause repair.",
            lookOutFor: ["Ground-fault alarms", "Manual reset dependence", "Wet-weather recurrence"],
          },
          {
            title: "Overvoltage sensitivity",
            severity: "Medium",
            summary: "Reactive power setup and transformer taps need close review on weak feeder connections.",
            lookOutFor: ["Peak-export trips", "Voltage outside limits", "Frequent clear-sky events"],
          },
          {
            title: "Cooling degradation",
            severity: "Medium",
            summary: "Ageing fans and dirty heat sinks can translate into avoidable summer derating.",
            lookOutFor: ["Fan alarms", "Heat sink fouling", "Output flattening in hot windows"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Delta",
    company: {
      name: "Delta Electronics",
      founded: "1971",
      headquarters: "Taipei, Taiwan",
      statLabel: "Positioning",
      statValue: "Broad power-electronics portfolio including utility-scale string and central inverters",
      overview:
        "Delta's solar inverter range spans string and central formats, making the brand relevant across commercial rooftop and utility-scale ground-mount portfolios.",
      website: "https://www.delta-emea.com",
      accent: "from-[#e03030] via-[#e85555] to-[#f09090]",
    },
    models: [
      {
        model: "MH250HV",
        specs: specLabel("inverter", "Delta", "MH250HV"),
        monitoringFocus: ["MPPT efficiency", "Fan health", "Insulation resistance trend"],
        issues: [
          {
            title: "Fan and cooling maintenance",
            severity: "Medium",
            summary: "String inverter fans can be a hidden availability risk when service intervals are not enforced.",
            lookOutFor: ["Fan alarms", "Cabinet temperature rise", "Output below peer units on calm days"],
          },
          {
            title: "Insulation resistance at string level",
            severity: "High",
            summary: "Wet-weather and aging connector insulation should be reviewed early on Delta fleets as on any string platform.",
            lookOutFor: ["Rain-linked trips", "Recurring low Riso", "Single MPPT trending lower than peers"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Fronius",
    company: {
      name: "Fronius International",
      founded: "1945",
      headquarters: "Pettenbach, Austria",
      statLabel: "Positioning",
      statValue: "European string inverter specialist with strong monitoring platform",
      overview:
        "Fronius is a respected European inverter brand, particularly well established in commercial and C&I markets, with the Solar.web monitoring ecosystem widely used on managed portfolios.",
      website: "https://www.fronius.com",
      accent: "from-[#e05c0a] via-[#f07820] to-[#f8ab60]",
    },
    models: [
      {
        model: "Tauro ECO 100-3-P",
        specs: specLabel("inverter", "Fronius", "Tauro ECO 100-3-P"),
        monitoringFocus: ["Arc-fault events", "Grid trip rate", "Solar.web data completeness"],
        issues: [
          {
            title: "Arc-fault detection sensitivity",
            severity: "High",
            summary: "Fronius AFCI implementation is thorough, meaning connector or cable faults surface quickly but can also generate nuisance events if not root-caused properly.",
            lookOutFor: ["Arc event clusters", "Repeated same-string events", "Visible cable damage"],
          },
          {
            title: "Grid trip thresholds",
            severity: "Medium",
            summary: "Fronius inverters can trip on voltage quality issues that other brands ride through, making grid connection quality important to review on new sites.",
            lookOutFor: ["Peak-export disconnections", "Voltage alarms at midday", "Site-wide short stops"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Power Electronics",
    company: {
      name: "Power Electronics",
      founded: "1996",
      headquarters: "Valencia, Spain",
      statLabel: "Positioning",
      statValue: "Utility-scale central and string inverter platform",
      overview:
        "Power Electronics (PE) is a European utility-scale inverter specialist with a strong installed base across large ground-mount solar plants in Spain and internationally.",
      website: "https://powerelectronics.com",
      accent: "from-[#1e40af] via-[#3b6dd1] to-[#79a3e8]",
    },
    models: [
      {
        model: "FS1500CU",
        specs: specLabel("inverter", "Power Electronics", "FS1500CU"),
        monitoringFocus: ["Contactor wear", "Cooling system performance", "Grid synchronisation events"],
        issues: [
          {
            title: "Contactor and switching wear",
            severity: "High",
            summary: "High-trip-count utility plants can age switching hardware quickly on central-format stations.",
            lookOutFor: ["Failed reconnects", "Relay alarms", "One skid consistently behind fleet"],
          },
          {
            title: "Thermal derating in summer",
            severity: "Medium",
            summary: "Central enclosures demand disciplined cooling maintenance to avoid generation losses during peak irradiance periods.",
            lookOutFor: ["Overtemperature alarms", "Output capping at midday", "Cooling unit faults"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "SolarEdge",
    company: {
      name: "SolarEdge Technologies",
      founded: "2006",
      headquarters: "Herzliya, Israel",
      statLabel: "Platform distinction",
      statValue: "DC-optimised inverter system with module-level monitoring",
      overview:
        "SolarEdge's DC power optimiser architecture provides module-level monitoring and MPPT, making it particularly relevant for sites with partial shading, complex roof geometry, or where granular module-level loss attribution is required.",
      website: "https://www.solaredge.com",
      accent: "from-[#e04010] via-[#f06030] to-[#f89a70]",
    },
    models: [
      {
        model: "SE166K",
        specs: specLabel("inverter", "SolarEdge", "SE166K"),
        monitoringFocus: ["Optimiser communication drop-outs", "Module-level production divergence", "Inverter AC output stability"],
        issues: [
          {
            title: "Optimiser communication gaps",
            severity: "High",
            summary: "Loss of optimiser telemetry can mask real production loss and make root-cause analysis unreliable.",
            lookOutFor: ["Offline optimiser counts", "Modules reporting zero", "Communication errors after maintenance"],
          },
          {
            title: "Arc-fault detection",
            severity: "High",
            summary: "SolarEdge AFCI monitors each string and should not be suppressed — arc events require physical investigation.",
            lookOutFor: ["AFCI alarms", "Repeated same-string events", "Post-weather event clusters"],
          },
          {
            title: "Optimiser degradation",
            severity: "Medium",
            summary: "Module-level optimisers add an extra failure layer that should be tracked for degradation and replacement rates.",
            lookOutFor: ["Higher-than-average optimiser replacement rates", "Silent module-level underperformance", "Ageing fleet RMA trends"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "KACO",
    company: {
      name: "KACO new energy",
      founded: "1999",
      headquarters: "Neckarsulm, Germany",
      statLabel: "Positioning",
      statValue: "European utility and C&I string and central inverter supplier",
      overview:
        "KACO new energy has an established European presence in utility and commercial solar, particularly on assets installed during the early build-out of German and Southern European solar markets.",
      website: "https://kaco-newenergy.com",
      accent: "from-[#1b6b2f] via-[#2d9648] to-[#6dca87]",
    },
    models: [
      {
        model: "blueplanet 150 TL3",
        specs: specLabel("inverter", "KACO", "blueplanet 150 TL3"),
        monitoringFocus: ["Insulation alarms", "Fan condition", "Grid voltage compliance"],
        issues: [
          {
            title: "Fan and cooling maintenance on older units",
            severity: "Medium",
            summary: "Older KACO string units in European fleets may have accumulated fan wear that is not visible until a hot summer puts sustained load on the cooling path.",
            lookOutFor: ["Fan faults", "Cabinet temperature rise", "Midday derating"],
          },
          {
            title: "Legacy monitoring connectivity",
            severity: "Info",
            summary: "Older KACO installations may use monitoring protocols that require gateway updates to integrate with modern O&M platforms.",
            lookOutFor: ["Data gaps", "Slow alarm propagation", "Mismatched Modbus register maps"],
          },
        ],
      },
    ],
  },
];

const moduleKnowledge: ManufacturerKnowledge[] = [
  {
    manufacturer: "First Solar",
    company: {
      name: "First Solar",
      founded: "1999",
      headquarters: "Tempe, Arizona, United States",
      statLabel: "Manufacturing scale",
      statValue: "~25 GW expected global annual nameplate capacity in 2026",
      overview:
        "First Solar is the largest thin-film utility-scale module specialist, with a strong CdTe performance position in hot-climate solar plants.",
      website: "https://www.firstsolar.com",
      accent: "from-[#f38a1f] via-[#f2a33c] to-[#f2c56f]",
    },
    models: [
      {
        model: "Series 6 Plus",
        specs: specLabel("module", "First Solar", "Series 6 Plus"),
        monitoringFocus: ["Soiling rate", "Wet-weather insulation behaviour", "Junction-box thermography"],
        issues: [
          {
            title: "Flat-glass soiling sensitivity",
            severity: "High",
            summary: "The REVEAL module knowledge base flags soiling as a major energy-loss lever on CdTe fleets in dry months.",
            lookOutFor: ["PR decline through dry season", "Recovery after rain", "Bird-fouling hotspots"],
          },
          {
            title: "Wet-weather insulation degradation",
            severity: "High",
            summary: "String insulation and moisture ingress still deserve close attention on older CdTe arrays.",
            lookOutFor: ["Rain-driven trips", "Low string insulation resistance", "Repeat alarms on same inverter block"],
          },
          {
            title: "Junction-box or bypass stress",
            severity: "Medium",
            summary: "Persistent local shading or moisture ingress can create hot junction boxes and open-circuit risk.",
            lookOutFor: ["Thermal hot spots", "Open strings", "Module-level IR anomalies"],
          },
        ],
      },
      {
        model: "Series 7",
        specs: specLabel("module", "First Solar", "Series 7"),
        monitoringFocus: ["Degradation benchmarking", "Hot-climate PR advantage", "Module IR campaigns"],
        issues: [
          {
            title: "Benchmarking against the right degradation curve",
            severity: "Info",
            summary: "Series generation matters when deciding whether observed PR decline is normal or a warranty issue.",
            lookOutFor: ["Unexpected year-on-year PR drop", "Mismatch with expected stabilisation", "Legacy vs newer back-contact assumptions"],
          },
          {
            title: "Surface contamination",
            severity: "Medium",
            summary: "Even high-temperature-performance modules still lose meaningful yield if cleaning strategy is too light.",
            lookOutFor: ["Summer PR drag", "Front-glass soiling", "Bird droppings not removed quickly"],
          },
          {
            title: "Localized thermal defects",
            severity: "Medium",
            summary: "Thin-film hot spots can be subtler than on c-Si, so thermography quality matters.",
            lookOutFor: ["Low delta-T hot regions", "Local fill-factor loss", "Post-hail anomaly clusters"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "LONGi",
    company: {
      name: "LONGi",
      founded: "2000",
      headquarters: "Xi'an, China",
      statLabel: "Global reach",
      statValue: "Manufacturing and sales presence in 150+ countries and regions",
      overview:
        "LONGi is one of the largest crystalline-silicon PV suppliers globally and a benchmark name for mono-PERC and large-format bifacial modules.",
      website: "https://www.longi.com",
      accent: "from-[#0f766e] via-[#15978d] to-[#55bfb7]",
    },
    models: [
      {
        model: "Hi-MO 5 LR5-72HPH",
        specs: specLabel("module", "LONGi", "Hi-MO 5 LR5-72HPH"),
        monitoringFocus: ["Year-1 degradation", "PID risk", "Cell-crack imaging"],
        issues: [
          {
            title: "LID and early-life settling",
            severity: "Info",
            summary: "Mono-PERC platforms should be benchmarked with expected early stabilisation rather than straight against nameplate.",
            lookOutFor: ["1-3% first-month PR gap", "Stabilisation after early irradiance", "Commissioning expectations misaligned with reality"],
          },
          {
            title: "LETID and heat-driven decline",
            severity: "Medium",
            summary: "Elevated cell temperatures can create a slower extra loss layer in the first years.",
            lookOutFor: ["Summer-year decline beyond normal LID", "Partial winter recovery", "Performance diverging from yield model"],
          },
          {
            title: "PID and micro-cracking",
            severity: "High",
            summary: "Older PERC-era systems still deserve structured checks for potential-induced degradation and cell cracking.",
            lookOutFor: ["Uniform string decline", "EL dark patches", "Humidity-linked underperformance"],
          },
        ],
      },
      {
        model: "Hi-MO 7 LR7-72HGD",
        specs: specLabel("module", "LONGi", "Hi-MO 7 LR7-72HGD"),
        monitoringFocus: ["Rear-side cleanliness", "Clamp positioning", "Bifacial gain validation"],
        issues: [
          {
            title: "Rear-side soiling",
            severity: "Medium",
            summary: "Expected bifacial gain can disappear quickly if the rear glass is ignored in O&M planning.",
            lookOutFor: ["Measured gain below model", "Dust or splatter on rear glass", "Low albedo benefit"],
          },
          {
            title: "Clamp-zone stress",
            severity: "High",
            summary: "Bifacial mounting zones are less forgiving when installers rush or over-torque.",
            lookOutFor: ["Stress signatures near clamps", "Power loss clustered by table", "Micro-cracking in EL"],
          },
          {
            title: "Cell-crack progression",
            severity: "Medium",
            summary: "Large-format cells deserve good EL baselining and periodic review after transport or hail events.",
            lookOutFor: ["New EL branches", "Inactive crack areas", "Module hot spots or snail trails"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Jinko Solar",
    company: {
      name: "Jinko Solar",
      founded: "2006",
      headquarters: "Shanghai, China",
      statLabel: "Market position",
      statValue: "Global utility-scale mono-PERC and N-type TOPCon supplier",
      overview:
        "Jinko Solar is one of the most visible module suppliers in utility-scale solar, especially across large mono-PERC and N-type TOPCon deployments.",
      website: "https://www.jinkosolar.com",
      accent: "from-[#003b8f] via-[#1b5fb8] to-[#5f93dd]",
    },
    models: [
      {
        model: "Tiger Pro 72HC",
        specs: specLabel("module", "Jinko Solar", "Tiger Pro 72HC"),
        monitoringFocus: ["LID/LETID trend", "Hotspot surveys", "EL imaging after handling events"],
        issues: [
          {
            title: "PERC stabilisation and LETID",
            severity: "Medium",
            summary: "As with other mono-PERC fleets, the first years should be trended carefully for extra heat-driven decline.",
            lookOutFor: ["Summer degradation beyond forecast", "PR not settling after initial months", "Hot-climate divergence"],
          },
          {
            title: "Micro-cracking on large-format cells",
            severity: "Medium",
            summary: "Transport, clamp loading, or hail can produce localized inactive cell regions with real output loss.",
            lookOutFor: ["EL cracks", "Snail trails", "Patchy module underperformance"],
          },
          {
            title: "Bypass-diode or hotspot risk",
            severity: "High",
            summary: "Persistent shading and fouling can cascade into thermal stress and disproportionate module losses.",
            lookOutFor: ["Hotspot signatures", "Junction-box heating", "One module dragging string current"],
          },
        ],
      },
      {
        model: "Tiger Neo 72HL4-BDV",
        specs: specLabel("module", "Jinko Solar", "Tiger Neo 72HL4-BDV"),
        monitoringFocus: ["Rear-side gain", "Clamp torque quality", "IR anomaly review"],
        issues: [
          {
            title: "Rear-side soiling or splashback",
            severity: "Medium",
            summary: "N-type bifacial performance is strong, but it still depends on rear irradiance reaching the cells.",
            lookOutFor: ["Underwhelming bifacial uplift", "Rear-glass contamination", "Low albedo conditions"],
          },
          {
            title: "Clamp-zone installation errors",
            severity: "High",
            summary: "Even premium bifacial modules remain sensitive to bad mounting geometry and overtightening.",
            lookOutFor: ["Stress bands near clamps", "Row-specific underperformance", "Micro-cracks in EL"],
          },
          {
            title: "Hotspot detection on large-format strings",
            severity: "Medium",
            summary: "Module size and string design make thermographic quality important during inspections.",
            lookOutFor: ["Thermal outliers", "Bird fouling", "Single modules limiting string current"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "JA Solar",
    company: {
      name: "JA Solar",
      founded: "2005",
      headquarters: "Beijing, China",
      statLabel: "Utility module platform",
      statValue: "DeepBlue utility-scale mono and TOPCon module family",
      overview:
        "JA Solar is a major utility-scale PV supplier with broad deployment across mono-PERC and newer n-type TOPCon projects.",
      website: "https://www.jasolar.com",
      accent: "from-[#0b5cab] via-[#2e7fd0] to-[#78ade8]",
    },
    models: [
      {
        model: "DeepBlue 4.0 Pro JAM72D40",
        specs: specLabel("module", "JA Solar", "DeepBlue 4.0 Pro JAM72D40"),
        monitoringFocus: ["Rear-side gain validation", "Thermography baselines", "Clamp-zone inspection"],
        issues: [
          {
            title: "Bifacial gain below forecast",
            severity: "Medium",
            summary: "Rear-side production assumptions should be checked against actual site albedo, row geometry, and soiling conditions.",
            lookOutFor: ["Low measured rear-side uplift", "Rear-glass contamination", "Row-to-row gain dispersion"],
          },
          {
            title: "Mounting and transport stress",
            severity: "High",
            summary: "Large-format bifacial modules remain sensitive to handling, torque, and clamp placement quality.",
            lookOutFor: ["EL crack signatures", "Hot spots near clamp zones", "Table-specific underperformance"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Canadian Solar",
    company: {
      name: "Canadian Solar",
      founded: "2001",
      headquarters: "Guelph, Ontario, Canada",
      statLabel: "Utility product line",
      statValue: "HiKu and BiHiKu families for large-format PV plants",
      overview:
        "Canadian Solar is a long-established global PV manufacturer with strong utility-scale deployment across bifacial and large-format module platforms.",
      website: "https://www.csisolar.com",
      accent: "from-[#1f4f9a] via-[#4372be] to-[#8faee0]",
    },
    models: [
      {
        model: "TOPBiHiKu6 CS6W",
        specs: specLabel("module", "Canadian Solar", "TOPBiHiKu6 CS6W"),
        monitoringFocus: ["Bifacial uplift tracking", "Row cleanliness", "String mismatch review"],
        issues: [
          {
            title: "Rear-side underperformance",
            severity: "Medium",
            summary: "Expected bifacial benefit can be overstated when rear irradiance conditions are weaker than design assumptions.",
            lookOutFor: ["Rear-side gain below model", "Contaminated lower glass", "Unexpected row mismatch"],
          },
          {
            title: "Large-format module mismatch",
            severity: "Medium",
            summary: "Electrical dispersion can become more visible on very large strings if commissioning tolerances are loose.",
            lookOutFor: ["String current spread", "Hot connectors", "Localized table losses"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Trina Solar",
    company: {
      name: "Trina Solar",
      founded: "1997",
      headquarters: "Changzhou, China",
      statLabel: "Flagship utility line",
      statValue: "Vertex utility module family above 600 W",
      overview:
        "Trina Solar is one of the leading large-format utility PV suppliers, especially through its high-power Vertex platform.",
      website: "https://www.trinasolar.com",
      accent: "from-[#0f6d6b] via-[#1e9b97] to-[#73c9c4]",
    },
    models: [
      {
        model: "Vertex N TSM-NEG19RC",
        specs: specLabel("module", "Trina Solar", "Vertex N TSM-NEG19RC"),
        monitoringFocus: ["Bifacial gain validation", "Clamp quality", "Hotspot surveillance"],
        issues: [
          {
            title: "Large-format handling stress",
            severity: "High",
            summary: "Transport, mounting, and tracker integration quality have a direct influence on crack risk for large-format modules.",
            lookOutFor: ["EL micro-cracks", "Clamp-zone hot areas", "Row-specific loss patterns"],
          },
          {
            title: "Thermal and soiling asymmetry",
            severity: "Medium",
            summary: "Large module footprints can amplify localized fouling and thermal non-uniformity when cleaning and inspection routines are weak.",
            lookOutFor: ["Thermal outliers", "Bird fouling clusters", "Current mismatch by string"],
          },
        ],
      },
    ],
  },
];

const bessKnowledge: ManufacturerKnowledge[] = [
  {
    manufacturer: "Tesla",
    company: {
      name: "Tesla Energy",
      founded: "2003",
      headquarters: "Austin, Texas, United States",
      statLabel: "Utility storage platform",
      statValue: "Megapack platform for multi-MW grid-scale storage",
      overview:
        "Tesla's Megapack is one of the most visible utility-scale storage products for standalone and hybrid renewable plants, with factory-integrated controls and high deployment volume.",
      website: "https://www.tesla.com/megapack",
      accent: "from-[#8e98a5] via-[#b3bbc5] to-[#d1d6dc]",
    },
    models: [
      {
        model: "Megapack 2 XL",
        specs: specLabel("bess", "Tesla", "Megapack 2 XL"),
        monitoringFocus: ["State-of-charge drift", "Thermal excursions", "Availability of PCS and auxiliaries"],
        issues: [
          {
            title: "Auxiliary-system outages reduce usable hours",
            severity: "High",
            summary: "Container uptime depends on HVAC, control, and protection subsystems as much as on battery health itself.",
            lookOutFor: ["HVAC faults", "Container offline alarms", "Reduced available capacity"],
          },
          {
            title: "Throughput-heavy dispatch accelerates wear",
            severity: "Medium",
            summary: "Aggressive arbitrage or ancillary-service duty can consume cycle life faster than simple renewable shifting duty.",
            lookOutFor: ["Equivalent full cycles", "Capacity fade", "Higher internal temperature"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Sungrow",
    company: {
      name: "Sungrow Storage",
      founded: "1997",
      headquarters: "Hefei, China",
      statLabel: "Platform family",
      statValue: "PowerTitan utility-scale liquid-cooled storage line",
      overview:
        "Sungrow combines PV inverter and utility-scale BESS integration capability, which makes it relevant for hybrid solar-plus-storage deployments in REVEAL.",
      website: "https://en.sungrowpower.com",
      accent: "from-[#f26f21] via-[#f58d3b] to-[#f8b35d]",
    },
    models: [
      {
        model: "PowerTitan 2.0",
        specs: specLabel("bess", "Sungrow", "PowerTitan 2.0"),
        monitoringFocus: ["String-level temperature spread", "PCS alarms", "Round-trip efficiency tracking"],
        issues: [
          {
            title: "Thermal imbalance between liquid-cooled racks",
            severity: "High",
            summary: "Cooling imbalance can quietly limit usable power or accelerate uneven battery ageing.",
            lookOutFor: ["Rack temperature delta", "Repeated thermal alarms", "Uneven SoC spread"],
          },
          {
            title: "PCS and battery dispatch mismatch",
            severity: "Medium",
            summary: "Hybrid plants need battery and converter limits aligned with the operating strategy actually used on site.",
            lookOutFor: ["Clipped discharge", "Charge refusal", "Dispatch not matching EMS command"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Fluence",
    company: {
      name: "Fluence",
      founded: "2018",
      headquarters: "Arlington, Virginia, United States",
      statLabel: "Storage specialization",
      statValue: "Dedicated grid-scale storage integrator",
      overview:
        "Fluence focuses on grid-scale storage platforms, controls, and optimization software, making it a strong reference for standalone storage performance tracking.",
      website: "https://fluenceenergy.com",
      accent: "from-[#2a6acb] via-[#4b8de0] to-[#8ab7f2]",
    },
    models: [
      {
        model: "Gridstack Pro",
        specs: specLabel("bess", "Fluence", "Gridstack Pro"),
        monitoringFocus: ["EMS command execution", "Cell temperature uniformity", "Availability by block"],
        issues: [
          {
            title: "Control-layer performance masks true battery capability",
            severity: "Medium",
            summary: "Poor dispatch logic can look like battery weakness when the root cause is controls or site integration.",
            lookOutFor: ["Command mismatch", "Unexpected curtailment", "Latency between schedule and delivery"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "CATL",
    company: {
      name: "CATL",
      founded: "2011",
      headquarters: "Ningde, China",
      statLabel: "Storage cell and system scale",
      statValue: "Utility-scale liquid-cooled ESS platforms including EnerC and TENER",
      overview:
        "CATL is one of the largest battery manufacturers globally and a major reference for utility-scale containerized storage systems.",
      website: "https://www.catl.com/en/solution/ess/",
      accent: "from-[#124b98] via-[#2e74cb] to-[#86b1ec]",
    },
    models: [
      {
        model: "EnerC Plus",
        specs: specLabel("bess", "CATL", "EnerC Plus"),
        monitoringFocus: ["Capacity retention", "Thermal stability", "Auxiliary load trend"],
        issues: [
          {
            title: "Thermal-management imbalance",
            severity: "High",
            summary: "Liquid-cooled container fleets should be reviewed for rack-to-rack temperature separation and auxiliary efficiency drift.",
            lookOutFor: ["Temperature delta by rack", "Rising auxiliary consumption", "Container derating"],
          },
          {
            title: "Cycle-life usage mismatch",
            severity: "Medium",
            summary: "Duty cycle assumptions need to remain aligned with the actual throughput and dispatch strategy used on site.",
            lookOutFor: ["Equivalent full cycles", "Capacity fade", "Unexpected internal resistance rise"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Wärtsilä",
    company: {
      name: "Wärtsilä",
      founded: "1834",
      headquarters: "Helsinki, Finland",
      statLabel: "Integrated storage platform",
      statValue: "GridSolv Quantum utility storage architecture",
      overview:
        "Wärtsilä combines storage hardware, controls, and grid-integration capability for utility-scale standalone and hybrid BESS projects.",
      website: "https://www.wartsila.com/energy/storage",
      accent: "from-[#ff8f1f] via-[#ffad4d] to-[#ffd08d]",
    },
    models: [
      {
        model: "Quantum",
        specs: specLabel("bess", "Wärtsilä", "Quantum"),
        monitoringFocus: ["Block availability", "Thermal management", "Control response quality"],
        issues: [
          {
            title: "Container availability constrained by auxiliaries",
            severity: "Medium",
            summary: "Auxiliary and control subsystem faults can reduce site availability even when battery state of health remains good.",
            lookOutFor: ["Auxiliary alarms", "Block downtime", "Dispatch not delivered"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "HiTHIUM",
    company: {
      name: "HiTHIUM",
      founded: "2019",
      headquarters: "Xiamen, China",
      statLabel: "High-density ESS line",
      statValue: "5-6.25 MWh liquid-cooled containerized BESS products",
      overview:
        "HiTHIUM is rapidly gaining visibility in grid-scale storage through high-density LFP container solutions aimed at utility deployment.",
      website: "https://en.hithium.com",
      accent: "from-[#355fda] via-[#5f86eb] to-[#9fb6f6]",
    },
    models: [
      {
        model: "∞Power 6.25MWh 4h",
        specs: specLabel("bess", "HiTHIUM", "∞Power 6.25MWh 4h"),
        monitoringFocus: ["Throughput profile", "Thermal uniformity", "RTE verification"],
        issues: [
          {
            title: "Energy-dense container thermal spread",
            severity: "High",
            summary: "High-density containers should be monitored closely for temperature separation and cooling-system stability under sustained duty.",
            lookOutFor: ["Cell temperature divergence", "Cooling alarms", "Available power reduction"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Connected Energy",
    company: {
      name: "Connected Energy",
      founded: "2012",
      headquarters: "Gateshead, United Kingdom",
      statLabel: "Technology platform",
      statValue: "Second-life EV battery storage systems for utility-scale retrofit and grid-edge projects",
      overview:
        "Connected Energy specialises in repurposing end-of-first-life EV batteries into containerized storage systems. In the French offer reflected in REVEAL, the utility-scale M-STOR configurations are deployed with separate SKID PCS and transformer units rather than the now-phasing-out E-STOR platform.",
      website: "https://www.connected.energy",
      accent: "from-[#00aa6e] via-[#25c285] to-[#6dddb4]",
    },
    models: [
      {
        model: "M-STOR 4.35 MW / 2.6 h",
        specs: specLabel("bess", "Connected Energy", "M-STOR 4.35 MW / 2.6 h"),
        monitoringFocus: ["State-of-health spread across repurposed EV battery containers", "PCS skid availability", "Delivered recoverable energy during negative-price windows"],
        issues: [
          {
            title: "Second-life container heterogeneity",
            severity: "High",
            summary: "Repurposed EV battery containers enter service with differing usage histories. Commissioning and ongoing operation should track state-of-health spread across the installed fleet.",
            lookOutFor: ["Container-to-container SoH divergence", "Premature capacity fade", "Unexpected derating of individual battery blocks"],
          },
          {
            title: "PCS and transformer skid bottlenecks",
            severity: "Medium",
            summary: "The deployed architecture couples multiple battery containers to shared PCS and transformer skids, so auxiliary outages can constrain a large block of storage capacity.",
            lookOutFor: ["Skid-level trips", "Power clipping at shared conversion units", "Availability loss concentrated on one conversion block"],
          },
          {
            title: "Thermal and balancing performance under cycling",
            severity: "Medium",
            summary: "Air-cooled second-life storage can show more pronounced thermal drift and balancing spread than first-life utility BESS during sustained cycling against curtailment events.",
            lookOutFor: ["RTE below expected level", "Summer temperature-linked derating", "State-of-charge imbalance alarms"],
          },
        ],
      },
    ],
  },
];

const windKnowledge: ManufacturerKnowledge[] = [
  {
    manufacturer: "Vestas",
    company: {
      name: "Vestas",
      founded: "1945",
      headquarters: "Aarhus, Denmark",
      statLabel: "Installed base",
      statValue: "185 GW+ installed in 88 countries",
      overview:
        "Vestas is the global wind market leader by installed base, with mature service practices and a very broad onshore and offshore fleet.",
      website: "https://www.vestas.com",
      accent: "from-[#00a3e0] via-[#35b7ea] to-[#7fd7f5]",
    },
    models: [
      {
        model: "V136-4.5",
        specs: specLabel("turbine", "Vestas", "V136-4.5"),
        monitoringFocus: ["Blade condition", "Yaw alignment", "Converter temperature"],
        issues: [
          {
            title: "Leading-edge erosion",
            severity: "Medium",
            summary: "Blade erosion can gradually drag annual energy and distort the power curve if left untreated.",
            lookOutFor: ["High-speed underperformance", "Visible edge damage", "Power-curve drift vs reference"],
          },
          {
            title: "Yaw alignment bias",
            severity: "Medium",
            summary: "Persistent yaw offset can flatten power output and increase structural loading.",
            lookOutFor: ["Negative yaw error bias", "Asymmetric loading", "Sector-independent curve loss"],
          },
          {
            title: "Converter cooling stress",
            severity: "Info",
            summary: "Thermal management should be watched closely during summer high-load periods.",
            lookOutFor: ["Converter temperature alarms", "Warm-weather derating", "One turbine lagging peers"],
          },
        ],
      },
      {
        model: "V150-4.5",
        specs: specLabel("turbine", "Vestas", "V150-4.5"),
        monitoringFocus: ["Power curve vs OEM", "Pitch system trend", "LEP campaign status"],
        issues: [
          {
            title: "Power-curve loss from blade condition",
            severity: "Medium",
            summary: "This rotor class is very sensitive to surface condition when benchmarked against OEM curves.",
            lookOutFor: ["Mid- and high-speed underperformance", "LEP degradation", "Turbine-to-turbine divergence"],
          },
          {
            title: "Pitch-system reliability",
            severity: "Medium",
            summary: "Pitch drives and backup systems should be trended before faults start stacking into availability loss.",
            lookOutFor: ["Pitch battery issues", "Pitch timeout alarms", "Emergency-stop resets"],
          },
          {
            title: "Wake-sensitive alignment drift",
            severity: "Info",
            summary: "Wake-heavy sites need clean yaw data to separate control issues from layout effects.",
            lookOutFor: ["Persistent yaw offset", "One wind sector underperforming", "High turbulence sensitivity"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Siemens Gamesa",
    company: {
      name: "Siemens Gamesa",
      founded: "2017",
      headquarters: "Zamudio, Spain",
      statLabel: "Positioning",
      statValue: "Global onshore and offshore wind OEM",
      overview:
        "Siemens Gamesa remains a major wind OEM with strong engineering depth and a wide fleet across both onshore and offshore applications.",
      website: "https://www.siemensgamesa.com",
      accent: "from-[#00b3a4] via-[#2bc5b8] to-[#79ddd4]",
    },
    models: [
      {
        model: "SG 5.0-145",
        specs: specLabel("turbine", "Siemens Gamesa", "SG 5.0-145"),
        monitoringFocus: ["Power curve", "Yaw and pitch events", "Converter behaviour"],
        issues: [
          {
            title: "Blade leading-edge erosion",
            severity: "Medium",
            summary: "Large rotor designs can hide meaningful energy loss if blade condition is not inspected routinely.",
            lookOutFor: ["High-speed power loss", "Visual LEP damage", "AEP drift vs benchmark"],
          },
          {
            title: "Pitch or yaw actuator wear",
            severity: "Medium",
            summary: "Mechanical control systems need periodic trending to avoid avoidable downtime.",
            lookOutFor: ["Pitch timeout alarms", "Yaw hunting", "Repeated controller resets"],
          },
          {
            title: "Converter or software events",
            severity: "Info",
            summary: "Firmware, controls, and converter stability deserve attention after resets or updates.",
            lookOutFor: ["Post-update alarms", "Converter resets", "Alarm bursts without site-level cause"],
          },
        ],
      },
      {
        model: "SG 14-236 DD",
        specs: specLabel("turbine", "Siemens Gamesa", "SG 14-236 DD"),
        monitoringFocus: ["Electrical health", "Blade condition", "Sensor quality"],
        issues: [
          {
            title: "Direct-drive electrical monitoring",
            severity: "Medium",
            summary: "Large offshore direct-drive machines reward close tracking of generator, converter, and cooling signatures.",
            lookOutFor: ["Electrical anomalies", "Cooling alarms", "Outlier temperature behaviour"],
          },
          {
            title: "Blade and edge-protection durability",
            severity: "Medium",
            summary: "Blade condition remains a bankable lever in offshore yield performance.",
            lookOutFor: ["Erosion progression", "Reduced output in higher wind bins", "Blade repair backlog"],
          },
          {
            title: "Sensor confidence before diagnosis",
            severity: "Info",
            summary: "SCADA quality and sensor consistency are essential before drawing conclusions from performance deltas.",
            lookOutFor: ["Anemometer discrepancies", "Yaw sensor drift", "Unexpected pitch behaviour"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "GE Vernova",
    company: {
      name: "GE Vernova Wind",
      founded: "2024",
      headquarters: "Cambridge, Massachusetts, United States",
      statLabel: "Installed wind base",
      statValue: "Nearly 120 GW and about 57,000 turbines",
      overview:
        "GE Vernova’s wind business combines a large legacy onshore fleet with global turbine and blade engineering capability.",
      website: "https://www.gevernova.com",
      accent: "from-[#005eb8] via-[#2f7fd0] to-[#76a8e4]",
    },
    models: [
      {
        model: "GE 4.8-158",
        specs: specLabel("turbine", "GE Vernova", "GE 4.8-158"),
        monitoringFocus: ["Pitch systems", "Converter cooling", "Blade condition"],
        issues: [
          {
            title: "Pitch backup-system reliability",
            severity: "Medium",
            summary: "Battery or backup-power health can quietly shape restart behaviour and fault rates.",
            lookOutFor: ["Pitch battery alarms", "Delayed restart", "Emergency-stop recoveries"],
          },
          {
            title: "Converter or cooling performance",
            severity: "Medium",
            summary: "Thermal outliers can become persistent lost-energy drivers if not trended early.",
            lookOutFor: ["Temperature alarms", "Warm-weather derate", "One turbine lagging in hot weather"],
          },
          {
            title: "Blade surface condition",
            severity: "Medium",
            summary: "Power-curve benchmarking should include blade erosion review before deeper drivetrain conclusions are drawn.",
            lookOutFor: ["High-speed power loss", "Visible erosion", "Sector-independent underperformance"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Enercon",
    company: {
      name: "Enercon",
      founded: "1984",
      headquarters: "Aurich, Germany",
      statLabel: "Technology platform",
      statValue: "Direct-drive onshore wind turbine specialist",
      overview:
        "Enercon is a longstanding wind OEM known for direct-drive turbine architecture and strong relevance in European onshore fleets.",
      website: "https://www.enercon.de",
      accent: "from-[#00a69c] via-[#31bcb3] to-[#79d7d1]",
    },
    models: [
      {
        model: "E-138 EP3",
        specs: specLabel("turbine", "Enercon", "E-138 EP3"),
        monitoringFocus: ["Power curve stability", "Direct-drive thermal trend", "Yaw alignment"],
        issues: [
          {
            title: "Direct-drive thermal stress",
            severity: "Medium",
            summary: "Converter and generator temperature behavior should be monitored closely during sustained production periods.",
            lookOutFor: ["Thermal alarms", "Warm-weather derating", "Unit-to-unit thermal spread"],
          },
          {
            title: "Blade and yaw performance drift",
            severity: "Medium",
            summary: "Rotor condition and alignment remain major determinants of power-curve stability across the fleet.",
            lookOutFor: ["Sector-dependent underperformance", "Yaw bias", "Leading-edge erosion"],
          },
        ],
      },
    ],
  },
  {
    manufacturer: "Nordex",
    company: {
      name: "Nordex Group",
      founded: "1985",
      headquarters: "Hamburg, Germany",
      statLabel: "Installed base",
      statValue: "53 GW+ installed across 40+ markets",
      overview:
        "Nordex has built a large global onshore fleet and is particularly strong in multi-megawatt turbines for space- and grid-constrained markets.",
      website: "https://www.nordex-online.com",
      accent: "from-[#003f88] via-[#2964aa] to-[#74a0d4]",
    },
    models: [
      {
        model: "N149/4.5",
        specs: specLabel("turbine", "Nordex", "N149/4.5"),
        monitoringFocus: ["Gearbox condition", "Pitch hydraulics", "Blade erosion"],
        issues: [
          {
            title: "Drivetrain condition",
            severity: "High",
            summary: "Large geared turbines reward disciplined SCADA and CMS review around the drivetrain.",
            lookOutFor: ["Gearbox vibration trend", "Oil alarms", "Repeated drivetrain warnings"],
          },
          {
            title: "Pitch-hydraulic wear",
            severity: "Medium",
            summary: "Pitch system wear can show up first as nuisance faults before clearer availability loss arrives.",
            lookOutFor: ["Pitch alarms", "Reset-heavy history", "Slow restart behaviour"],
          },
          {
            title: "Blade leading-edge erosion",
            severity: "Medium",
            summary: "Rotor growth magnifies the yield impact of even moderate erosion progression.",
            lookOutFor: ["Power-curve drag", "Visible edge wear", "Underperformance above rated transition"],
          },
        ],
      },
    ],
  },
];

const syncedModuleKnowledge = synchronizeKnowledgeModels(moduleKnowledge, "module");
const syncedWindKnowledge = synchronizeKnowledgeModels(windKnowledge, "turbine");
const syncedBessKnowledge = synchronizeKnowledgeModels(bessKnowledge, "bess");

export const knowledgeBase: CategoryKnowledge[] = [
  {
    key: "inverter",
    label: { en: "Solar Inverters", fr: "Onduleurs solaires" },
    description: {
      en: "Utility-scale inverter OEMs, typical failure themes, and what to inspect first when REVEAL flags performance or availability losses.",
      fr: "OEM d’onduleurs utility-scale, thèmes de défaillance typiques et premiers contrôles à mener lorsque REVEAL détecte des pertes de performance ou de disponibilité.",
    },
    manufacturers: inverterKnowledge.filter((item) => inverterManufacturers.includes(item.manufacturer)),
  },
  {
    key: "module",
    label: { en: "Solar Modules", fr: "Modules solaires" },
    description: {
      en: "Module suppliers, degradation watchouts, installation-quality themes, and thermographic or EL cues worth tracking.",
      fr: "Fournisseurs de modules, points de vigilance liés à la dégradation, à la qualité d’installation et aux indices thermographiques ou EL à suivre.",
    },
    manufacturers: syncedModuleKnowledge.filter((item) => moduleManufacturers.includes(item.manufacturer)),
  },
  {
    key: "turbine",
    label: { en: "Wind Turbines", fr: "Éoliennes" },
    description: {
      en: "Indicative OEM summaries and the practical reliability themes Dolfines teams usually review first on wind assets.",
      fr: "Synthèses indicatives par OEM et thèmes de fiabilité que les équipes Dolfines regardent en priorité sur les actifs éoliens.",
    },
    manufacturers: syncedWindKnowledge.filter((item) => windManufacturers.includes(item.manufacturer)),
  },
  {
    key: "bess",
    label: { en: "BESS Containers", fr: "Conteneurs BESS" },
    description: {
      en: "Grid-scale storage platforms, key dispatch assumptions, and the utility-scale battery health signals REVEAL should track first.",
      fr: "Plateformes de stockage à l’échelle réseau, principales hypothèses d’exploitation et signaux de santé batterie que REVEAL doit suivre en priorité.",
    },
    manufacturers: syncedBessKnowledge.filter((item) => bessManufacturers.includes(item.manufacturer)),
  },
];

export function getCategoryKnowledge(category: EquipmentCategory) {
  return knowledgeBase.find((item) => item.key === category) ?? knowledgeBase[0];
}

export function getCompanyLogoUrl(company: CompanyProfile) {
  return logoUrl(company.website);
}

export function getManufacturerModels(category: EquipmentCategory, manufacturer: string) {
  if (category === "inverter") return getSolarInverterModels(manufacturer);
  if (category === "module") return getSolarModuleModels(manufacturer);
  if (category === "bess") return getBessModels(manufacturer);
  return getWindModels(manufacturer);
}
