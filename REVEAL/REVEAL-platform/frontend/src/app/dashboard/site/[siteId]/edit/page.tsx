"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import { api } from "@/lib/api";
import { useSite } from "@/hooks/useSites";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import {
  detectBessManufacturer,
  getBessManufacturers,
  getBessModels,
  getBessSpec,
  detectSolarInverterManufacturer,
  detectSolarModuleManufacturer,
  detectWindManufacturer,
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
import { useTranslation } from "@/lib/i18n";
import type { Site, SiteStatus, SiteType, SolarInverterUnit } from "@/types/site";

type SiteFormState = {
  display_name: string;
  country: string;
  region: string;
  lat: string;
  lon: string;
  cod: string;
  technology: string;
  solar_type: string;
  site_type: SiteType;
  status: SiteStatus;
  cap_ac_kw: string;
  cap_dc_kwp: string;
  n_inverters: string;
  inv_ac_kw: string;
  inv_model: string;
  n_modules: string;
  module_wp: string;
  module_brand: string;
  site_timezone: string;
  irradiance_basis: string;
  module_tilt_deg: string;
  tariff_eur_mwh: string;
  has_bess: boolean;
  bess_power_kw: string;
  bess_energy_kwh: string;
  bess_manufacturer: string;
  bess_model: string;
  bess_chemistry: string;
  bess_duration_hours: string;
  bess_roundtrip_efficiency_pct: string;
  bess_container_count: string;
  retrofit_bess_enabled: boolean;
  retrofit_bess_power_kw: string;
  retrofit_bess_energy_kwh: string;
  retrofit_bess_cost_eur_kwh: string;
  retrofit_bess_land_area_m2: string;
  dc_ac_ratio: string;
  design_pr: string;
  interval_min: string;
  irr_threshold: string;
  hub_height_m: string;
  tip_height_m: string;
  rotor_diameter_m: string;
  expected_aep_gwh: string;
};

type PrefillState = {
  turbineManufacturer: string;
  turbineModel: string;
  moduleManufacturer: string;
  moduleModel: string;
  inverterManufacturer: string;
  inverterModel: string;
  bessManufacturer: string;
  bessModel: string;
};

const EMPTY_FORM: SiteFormState = {
  display_name: "",
  country: "",
  region: "",
  lat: "0",
  lon: "0",
  cod: "",
  technology: "",
  solar_type: "ground-mounted",
  site_type: "solar",
  status: "operational",
  cap_ac_kw: "0",
  cap_dc_kwp: "0",
  n_inverters: "0",
  inv_ac_kw: "0",
  inv_model: "",
  n_modules: "0",
  module_wp: "0",
  module_brand: "",
  site_timezone: "Europe/Paris",
  irradiance_basis: "poa",
  module_tilt_deg: "",
  tariff_eur_mwh: "",
  has_bess: false,
  bess_power_kw: "",
  bess_energy_kwh: "",
  bess_manufacturer: "",
  bess_model: "",
  bess_chemistry: "",
  bess_duration_hours: "",
  bess_roundtrip_efficiency_pct: "",
  bess_container_count: "",
  retrofit_bess_enabled: false,
  retrofit_bess_power_kw: "",
  retrofit_bess_energy_kwh: "",
  retrofit_bess_cost_eur_kwh: "200",
  retrofit_bess_land_area_m2: "",
  dc_ac_ratio: "1",
  design_pr: "80",
  interval_min: "15",
  irr_threshold: "50",
  hub_height_m: "0",
  tip_height_m: "0",
  rotor_diameter_m: "0",
  expected_aep_gwh: "0",
};

const EMPTY_PREFILL: PrefillState = {
  turbineManufacturer: "",
  turbineModel: "",
  moduleManufacturer: "",
  moduleModel: "",
  inverterManufacturer: "",
  inverterModel: "",
  bessManufacturer: "",
  bessModel: "",
};

const OTHER_OPTION = "__other__";

const COUNTRY_SUGGESTIONS = [
  "UAE",
  "United Arab Emirates",
  "Afghanistan",
  "Albania",
  "Algeria",
  "Andorra",
  "Angola",
  "Antigua and Barbuda",
  "Argentina",
  "Armenia",
  "Australia",
  "Austria",
  "Azerbaijan",
  "Bahamas",
  "Bahrain",
  "Bangladesh",
  "Barbados",
  "Belarus",
  "Belgium",
  "Belize",
  "Benin",
  "Bhutan",
  "Bolivia",
  "Bosnia and Herzegovina",
  "Botswana",
  "Brazil",
  "Brunei",
  "Bulgaria",
  "Burkina Faso",
  "Burundi",
  "Cabo Verde",
  "Cambodia",
  "Cameroon",
  "Canada",
  "Central African Republic",
  "Chad",
  "Chile",
  "China",
  "Colombia",
  "Comoros",
  "Congo",
  "Costa Rica",
  "Cote d'Ivoire",
  "Croatia",
  "Cuba",
  "Cyprus",
  "Czech Republic",
  "Democratic Republic of the Congo",
  "Denmark",
  "Djibouti",
  "Dominica",
  "Dominican Republic",
  "Ecuador",
  "Egypt",
  "El Salvador",
  "Equatorial Guinea",
  "Eritrea",
  "Estonia",
  "Eswatini",
  "Ethiopia",
  "Fiji",
  "Finland",
  "France",
  "Gabon",
  "Gambia",
  "Georgia",
  "Germany",
  "Ghana",
  "Greece",
  "Grenada",
  "Guatemala",
  "Guinea",
  "Guinea-Bissau",
  "Guyana",
  "Haiti",
  "Honduras",
  "Hungary",
  "Iceland",
  "India",
  "Indonesia",
  "Iran",
  "Iraq",
  "Ireland",
  "Israel",
  "Italy",
  "Jamaica",
  "Japan",
  "Jordan",
  "Kazakhstan",
  "Kenya",
  "Kiribati",
  "Kuwait",
  "Kyrgyzstan",
  "Laos",
  "Latvia",
  "Lebanon",
  "Lesotho",
  "Liberia",
  "Libya",
  "Liechtenstein",
  "Lithuania",
  "Luxembourg",
  "Madagascar",
  "Malawi",
  "Malaysia",
  "Maldives",
  "Mali",
  "Malta",
  "Marshall Islands",
  "Mauritania",
  "Mauritius",
  "Mexico",
  "Micronesia",
  "Moldova",
  "Monaco",
  "Mongolia",
  "Montenegro",
  "Morocco",
  "Mozambique",
  "Myanmar",
  "Namibia",
  "Nauru",
  "Nepal",
  "Netherlands",
  "New Zealand",
  "Nicaragua",
  "Niger",
  "Nigeria",
  "North Korea",
  "North Macedonia",
  "Norway",
  "Oman",
  "Pakistan",
  "Palau",
  "Palestine",
  "Panama",
  "Papua New Guinea",
  "Paraguay",
  "Peru",
  "Philippines",
  "Poland",
  "Portugal",
  "Qatar",
  "Romania",
  "Russia",
  "Rwanda",
  "Saint Kitts and Nevis",
  "Saint Lucia",
  "Saint Vincent and the Grenadines",
  "Samoa",
  "San Marino",
  "Sao Tome and Principe",
  "Saudi Arabia",
  "Senegal",
  "Serbia",
  "Seychelles",
  "Sierra Leone",
  "Singapore",
  "Slovakia",
  "Slovenia",
  "Solomon Islands",
  "Somalia",
  "South Africa",
  "South Korea",
  "South Sudan",
  "Spain",
  "Sri Lanka",
  "Sudan",
  "Suriname",
  "Sweden",
  "Switzerland",
  "Syria",
  "Taiwan",
  "Tajikistan",
  "Tanzania",
  "Thailand",
  "Timor-Leste",
  "Togo",
  "Tonga",
  "Trinidad and Tobago",
  "Tunisia",
  "Turkey",
  "Turkmenistan",
  "Tuvalu",
  "Uganda",
  "Ukraine",
  "United Kingdom",
  "United States",
  "Uruguay",
  "Uzbekistan",
  "Vanuatu",
  "Vatican City",
  "Venezuela",
  "Vietnam",
  "Yemen",
  "Zambia",
  "Zimbabwe",
];

const REGION_SUGGESTIONS: Record<string, string[]> = {
  "united arab emirates": ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"],
  france: ["Nouvelle-Aquitaine", "Occitanie", "Provence-Alpes-Cote d'Azur", "Grand Est", "Auvergne-Rhone-Alpes"],
  germany: ["Bavaria", "Brandenburg", "Lower Saxony", "North Rhine-Westphalia", "Saxony-Anhalt"],
  spain: ["Andalusia", "Castile-La Mancha", "Extremadura", "Aragon", "Murcia"],
  morocco: ["Ouarzazate", "Laayoune-Sakia El Hamra", "Dakhla-Oued Ed-Dahab", "Marrakech-Safi"],
};

function normalizeCountryKey(value: string) {
  const key = value.trim().toLowerCase();
  if (["uae", "u.a.e.", "emirates", "united arab emirates"].includes(key)) return "united arab emirates";
  if (["uk", "u.k.", "united kingdom", "great britain", "england"].includes(key)) return "united kingdom";
  if (["usa", "u.s.a.", "united states", "united states of america"].includes(key)) return "united states";
  return key;
}

function inferTimezone(country: string, region: string) {
  const normalizedCountry = normalizeCountryKey(country);
  const normalizedRegion = region.trim().toLowerCase();

  if (normalizedCountry === "united arab emirates") return "Asia/Dubai";
  if (normalizedCountry === "france") return "Europe/Paris";
  if (normalizedCountry === "germany") return "Europe/Berlin";
  if (normalizedCountry === "spain") return "Europe/Madrid";
  if (normalizedCountry === "italy") return "Europe/Rome";
  if (normalizedCountry === "portugal") return "Europe/Lisbon";
  if (normalizedCountry === "united kingdom") return "Europe/London";
  if (normalizedCountry === "ireland") return "Europe/Dublin";
  if (normalizedCountry === "morocco") return "Africa/Casablanca";
  if (normalizedCountry === "saudi arabia") return "Asia/Riyadh";
  if (normalizedCountry === "oman") return "Asia/Muscat";
  if (normalizedCountry === "qatar") return "Asia/Qatar";
  if (normalizedCountry === "bahrain") return "Asia/Bahrain";
  if (normalizedCountry === "kuwait") return "Asia/Kuwait";
  if (normalizedCountry === "jordan") return "Asia/Amman";
  if (normalizedCountry === "egypt") return "Africa/Cairo";
  if (normalizedCountry === "turkey") return "Europe/Istanbul";
  if (normalizedCountry === "india") return "Asia/Kolkata";
  if (normalizedCountry === "australia") {
    if (/perth|western australia/.test(normalizedRegion)) return "Australia/Perth";
    if (/brisbane|queensland/.test(normalizedRegion)) return "Australia/Brisbane";
    if (/adelaide|south australia/.test(normalizedRegion)) return "Australia/Adelaide";
    if (/darwin|northern territory/.test(normalizedRegion)) return "Australia/Darwin";
    if (/sydney|melbourne|canberra|tasmania|victoria|new south wales|act/.test(normalizedRegion)) return "Australia/Sydney";
  }
  if (normalizedCountry === "canada") {
    if (/alberta|calgary|edmonton/.test(normalizedRegion)) return "America/Edmonton";
    if (/british columbia|vancouver/.test(normalizedRegion)) return "America/Vancouver";
    if (/ontario|toronto|ottawa/.test(normalizedRegion)) return "America/Toronto";
    if (/quebec|montreal/.test(normalizedRegion)) return "America/Montreal";
  }
  if (normalizedCountry === "united states") {
    if (/california|nevada|washington|oregon|arizona|los angeles|san francisco|phoenix|seattle/.test(normalizedRegion)) return "America/Los_Angeles";
    if (/texas|illinois|colorado|minnesota|utah|chicago|houston|dallas|denver/.test(normalizedRegion)) return "America/Chicago";
    if (/new york|florida|massachusetts|virginia|georgia|miami|boston|atlanta|washington dc/.test(normalizedRegion)) return "America/New_York";
  }
  return "";
}

function composeInverterDescriptor(manufacturer: string, model: string) {
  return [manufacturer.trim(), model.trim()].filter(Boolean).join(" ");
}

function parseInverterDescriptor(invModel: string) {
  const descriptor = invModel.trim();
  if (!descriptor) {
    return { manufacturer: "", model: "" };
  }

  const knownManufacturer = detectSolarInverterManufacturer(descriptor);
  if (knownManufacturer) {
    const normalizedDescriptor = descriptor.toLowerCase();
    const knownModel =
      getSolarInverterModels(knownManufacturer).find((model) => normalizedDescriptor.includes(model.toLowerCase())) ?? "";

    if (knownModel) {
      return { manufacturer: knownManufacturer, model: knownModel };
    }

    const manufacturerPrefix = descriptor.slice(0, knownManufacturer.length).trim();
    const remainder = descriptor.slice(knownManufacturer.length).trim();
    return {
      manufacturer: manufacturerPrefix || knownManufacturer,
      model: remainder,
    };
  }

  const parts = descriptor.split(/\s+/).filter(Boolean);
  if (parts.length <= 1) {
    return { manufacturer: descriptor, model: "" };
  }

  return {
    manufacturer: parts[0],
    model: parts.slice(1).join(" "),
  };
}

function toInputDate(value: string) {
  if (!value) return "";
  const [day, month, year] = value.split("/");
  if (!day || !month || !year) return "";
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function toUiDate(value: string) {
  if (!value) return "";
  const [year, month, day] = value.split("-");
  if (!day || !month || !year) return "";
  return `${day}/${month}/${year}`;
}

function optionalNumber(value: string) {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : undefined;
}

function nullableNumber(value: string) {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : null;
}

function nullableInteger(value: string) {
  const trimmed = value.trim();
  return trimmed ? Number.parseInt(trimmed, 10) : null;
}

function mapSiteToForm(site: Site): SiteFormState {
  return {
    display_name: site.display_name,
    country: site.country,
    region: site.region,
    lat: String(site.lat ?? 0),
    lon: String(site.lon ?? 0),
    cod: toInputDate(site.cod),
    technology: site.technology,
    solar_type:
      site.site_type === "solar" && site.technology.toLowerCase().includes("floating")
        ? "floating"
        : site.site_type === "solar" && site.technology.toLowerCase().includes("agri")
          ? "agri-pv"
          : site.site_type === "solar" && site.technology.toLowerCase().includes("carport")
            ? "carport"
            : site.site_type === "solar" && site.technology.toLowerCase().includes("roof")
              ? "rooftop"
              : "ground-mounted",
    site_type: site.site_type,
    status: site.status,
    cap_ac_kw: String(site.cap_ac_kw),
    cap_dc_kwp: String(site.cap_dc_kwp),
    n_inverters: String(site.n_inverters),
    inv_ac_kw: String(site.inv_ac_kw),
    inv_model: site.inv_model,
    n_modules: String(site.n_modules),
    module_wp: String(site.module_wp),
    module_brand: site.module_brand,
    site_timezone: site.site_timezone ?? "Europe/Paris",
    irradiance_basis: site.irradiance_basis ?? "poa",
    module_tilt_deg: site.module_tilt_deg != null ? String(site.module_tilt_deg) : "",
    tariff_eur_mwh: site.tariff_eur_mwh != null ? String(site.tariff_eur_mwh) : "",
    has_bess: site.has_bess ?? false,
    bess_power_kw: site.bess_power_kw != null ? String(site.bess_power_kw) : "",
    bess_energy_kwh: site.bess_energy_kwh != null ? String(site.bess_energy_kwh) : "",
    bess_manufacturer: site.bess_manufacturer ?? "",
    bess_model: site.bess_model ?? "",
    bess_chemistry: site.bess_chemistry ?? "",
    bess_duration_hours: site.bess_duration_hours != null ? String(site.bess_duration_hours) : "",
    bess_roundtrip_efficiency_pct: site.bess_roundtrip_efficiency_pct != null ? String(site.bess_roundtrip_efficiency_pct) : "",
    bess_container_count: site.bess_container_count != null ? String(site.bess_container_count) : "",
    retrofit_bess_enabled: site.retrofit_bess_enabled ?? false,
    retrofit_bess_power_kw: site.retrofit_bess_power_kw != null ? String(site.retrofit_bess_power_kw) : "",
    retrofit_bess_energy_kwh: site.retrofit_bess_energy_kwh != null ? String(site.retrofit_bess_energy_kwh) : "",
    retrofit_bess_cost_eur_kwh: site.retrofit_bess_cost_eur_kwh != null ? String(site.retrofit_bess_cost_eur_kwh) : "200",
    retrofit_bess_land_area_m2: site.retrofit_bess_land_area_m2 != null ? String(site.retrofit_bess_land_area_m2) : "",
    dc_ac_ratio: String(site.dc_ac_ratio),
    design_pr: decimalToPercentString(site.design_pr),
    interval_min: String(site.interval_min),
    irr_threshold: String(site.irr_threshold),
    hub_height_m: String(site.hub_height_m ?? 0),
    tip_height_m: String(site.tip_height_m ?? 0),
    rotor_diameter_m: String(site.rotor_diameter_m ?? 0),
    expected_aep_gwh: String(site.expected_aep_gwh ?? 0),
  };
}

function inferPrefillState(site: Site): PrefillState {
  const turbineManufacturer = detectWindManufacturer(site.technology);
  const primaryModuleType = site.solar_module_types?.[0];
  const moduleManufacturer = primaryModuleType?.manufacturer || detectSolarModuleManufacturer(site.module_brand || site.technology);
  const parsedInverter = parseInverterDescriptor(site.inv_model);
  const inverterManufacturer = parsedInverter.manufacturer;
  const knownInverterManufacturer = detectSolarInverterManufacturer(site.inv_model);
  const knownInverterModel = knownInverterManufacturer
    ? getSolarInverterModels(knownInverterManufacturer).find((model) => site.inv_model.toLowerCase().includes(model.toLowerCase())) ?? ""
    : "";
  const bessManufacturer = site.bess_manufacturer || detectBessManufacturer(site.bess_model || "");
  const bessModel = bessManufacturer
    ? getBessModels(bessManufacturer).find((model) => (site.bess_model || "").toLowerCase().includes(model.toLowerCase())) ?? site.bess_model ?? ""
    : site.bess_model ?? "";

  return {
    turbineManufacturer,
    turbineModel: turbineManufacturer
      ? getWindModels(turbineManufacturer).find((model) => site.technology.toLowerCase().includes(model.toLowerCase())) ?? ""
      : "",
    moduleManufacturer,
    moduleModel: primaryModuleType?.model ?? (moduleManufacturer
      ? getSolarModuleModels(moduleManufacturer).find((model) => site.technology.toLowerCase().includes(model.toLowerCase())) ?? ""
      : ""),
    inverterManufacturer,
    inverterModel: knownInverterModel || parsedInverter.model,
    bessManufacturer,
    bessModel,
  };
}

function fieldClassName() {
  return "w-full rounded-lg border border-navy-light bg-navy-dark px-3 py-2 text-sm text-slate-100 outline-none transition-colors [color-scheme:dark] placeholder:text-slate-500 focus:border-orange-DEFAULT";
}

function SuggestionField({
  value,
  onChange,
  suggestions,
  placeholder,
  required,
}: {
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
  placeholder?: string;
  required?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const filteredSuggestions = useMemo(() => {
    const search = value.trim().toLowerCase();
    if (!search) return suggestions.slice(0, 8);
    return suggestions
      .filter((item) => item.toLowerCase().includes(search))
      .slice(0, 8);
  }, [suggestions, value]);

  return (
    <div className="relative">
      <input
        className={fieldClassName()}
        value={value}
        onFocus={(event) => {
          selectAllOnFocus(event);
          setOpen(true);
        }}
        onBlur={() => {
          window.setTimeout(() => setOpen(false), 120);
        }}
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        placeholder={placeholder}
        required={required}
      />
      {open && filteredSuggestions.length > 0 ? (
        <div className="absolute z-30 mt-2 max-h-56 w-full overflow-y-auto rounded-2xl border border-white/10 bg-[rgba(4,18,30,0.98)] p-2 shadow-[0_16px_48px_rgba(0,0,0,0.45)] backdrop-blur-sm">
          <div className="space-y-1">
            {filteredSuggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  onChange(suggestion);
                  setOpen(false);
                }}
                className="w-full rounded-xl border border-transparent px-3 py-2 text-left text-sm text-slate-100 transition hover:border-white/10 hover:bg-white/6"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function sectionTitle(title: string) {
  return <h2 className="font-dolfines text-lg font-semibold tracking-[0.06em] text-white">{title}</h2>;
}

function selectAllOnFocus(event: React.FocusEvent<HTMLInputElement>) {
  event.currentTarget.select();
}

function decimalInputProps() {
  return {
    lang: "en",
    inputMode: "decimal" as const,
    onFocus: selectAllOnFocus,
  };
}

function integerInputProps() {
  return {
    inputMode: "numeric" as const,
    onFocus: selectAllOnFocus,
  };
}

type InverterCapacityDraft = {
  tag: string;
  module_count: string;
  dc_capacity_kwp: string;
};

function sanitizeDecimalDraft(value: string) {
  const normalized = value.replace(/,/g, ".");
  if (normalized === "" || normalized === ".") {
    return normalized;
  }
  return /^\d*(\.\d*)?$/.test(normalized) ? normalized : null;
}

function parseDecimalDraft(value: string) {
  const normalized = value.replace(/,/g, ".").trim();
  if (normalized === "" || normalized === ".") {
    return 0;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeDecimalInput(value: string) {
  return value.replace(/,/g, ".");
}

function decimalToPercentString(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "";
  return String(Number((value * 100).toFixed(2)));
}

function percentStringToDecimal(value: string) {
  const normalized = Number(normalizeDecimalInput(value));
  if (!Number.isFinite(normalized)) return 0;
  return normalized / 100;
}

function estimateRetrofitBessLandAreaM2(energyKwh: number, containerCount: number, areaWithAccessM2?: number) {
  const energyMwh = Math.max(energyKwh, 0) / 1000;
  const byEnergy = energyMwh * 30;
  const byContainer = containerCount > 0 ? containerCount * (areaWithAccessM2 ?? 120) : 0;
  return Number(Math.max(byEnergy, byContainer).toFixed(1));
}

export default function SiteEditPage({ params }: { params: { siteId: string } }) {
  const { t } = useTranslation();
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const isNewSite = params.siteId === "new";
  const { site, isLoading } = useSite(isNewSite ? "" : params.siteId);
  const [form, setForm] = useState<SiteFormState>(EMPTY_FORM);
  const [prefill, setPrefill] = useState<PrefillState>(EMPTY_PREFILL);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inverterCapacities, setInverterCapacities] = useState<InverterCapacityDraft[]>([]);
  const [lastAutoTimezone, setLastAutoTimezone] = useState("");

  useEffect(() => {
    if (site && !isNewSite) {
      setForm(mapSiteToForm(site));
      setPrefill(inferPrefillState(site));
      setLastAutoTimezone("");
    }
  }, [isNewSite, site]);

  useEffect(() => {
    const suggestedTimezone = inferTimezone(form.country, form.region);
    if (!suggestedTimezone) return;
    setForm((current) => {
      const shouldApply =
        !current.site_timezone.trim() ||
        current.site_timezone === lastAutoTimezone ||
        current.site_timezone === "Europe/Paris";
      if (!shouldApply || current.site_timezone === suggestedTimezone) return current;
      return { ...current, site_timezone: suggestedTimezone };
    });
    setLastAutoTimezone(suggestedTimezone);
  }, [form.country, form.region, lastAutoTimezone]);

  useEffect(() => {
    if (site?.site_type === "solar") {
      const fromDb = site.solar_inverter_units ?? [];
      if (fromDb.length > 0) {
        setInverterCapacities(
          fromDb.map((item) => ({
            tag: item.tag,
            module_count:
              item.module_count != null
                ? String(item.module_count)
                : site.module_wp > 0
                  ? String(Math.round((item.dc_capacity_kwp * 1000) / site.module_wp))
                  : "",
            dc_capacity_kwp: String(item.dc_capacity_kwp),
          }))
        );
        return;
      }
      if (site.n_inverters > 0) {
        const unitCapacity = site.n_inverters > 0 ? Number(site.cap_dc_kwp) / site.n_inverters : 0;
        setInverterCapacities(
          Array.from({ length: site.n_inverters }, (_, index) => ({
            tag: `INV${index + 1}`,
            module_count: site.module_wp > 0 ? String(Math.round((unitCapacity * 1000) / site.module_wp)) : "",
            dc_capacity_kwp: String(Number(unitCapacity.toFixed(2))),
          }))
        );
        return;
      }
    }
    if (isNewSite) {
      setInverterCapacities([]);
    }
  }, [isNewSite, site]);

  const backHref = useMemo(() => (isNewSite ? "/dashboard" : `/dashboard/site/${params.siteId}`), [isNewSite, params.siteId]);
  const backLabel = isNewSite ? t("common.backToDashboard") : t("common.backToSite");
  const regionSuggestions = useMemo(() => REGION_SUGGESTIONS[normalizeCountryKey(form.country)] ?? [], [form.country]);

  const windManufacturers = getWindManufacturers();
  const windModels = prefill.turbineManufacturer ? getWindModels(prefill.turbineManufacturer) : [];
  const windManufacturerOptions = windManufacturers as readonly string[];
  const isCustomWindManufacturer = Boolean(prefill.turbineManufacturer) && !windManufacturerOptions.includes(prefill.turbineManufacturer);
  const isCustomWindModel = Boolean(prefill.turbineModel) && !windModels.includes(prefill.turbineModel);
  const moduleManufacturers = getSolarModuleManufacturers();
  const moduleManufacturerOptions = moduleManufacturers as readonly string[];
  const moduleModels = moduleManufacturerOptions.includes(prefill.moduleManufacturer)
    ? getSolarModuleModels(prefill.moduleManufacturer as (typeof moduleManufacturers)[number])
    : [];
  const inverterManufacturers = getSolarInverterManufacturers();
  const inverterManufacturerOptions = inverterManufacturers as readonly string[];
  const inverterModels = inverterManufacturerOptions.includes(prefill.inverterManufacturer)
    ? getSolarInverterModels(prefill.inverterManufacturer as (typeof inverterManufacturers)[number])
    : [];
  const bessManufacturers = getBessManufacturers();
  const bessManufacturerOptions = bessManufacturers as readonly string[];
  const bessModels = bessManufacturerOptions.includes(prefill.bessManufacturer)
    ? getBessModels(prefill.bessManufacturer as (typeof bessManufacturers)[number])
    : [];
  const isCustomModuleManufacturer = Boolean(prefill.moduleManufacturer) && !moduleManufacturerOptions.includes(prefill.moduleManufacturer);
  const isCustomModuleModel = Boolean(prefill.moduleModel) && !moduleModels.includes(prefill.moduleModel);
  const isCustomInverterManufacturer = Boolean(prefill.inverterManufacturer) && !inverterManufacturerOptions.includes(prefill.inverterManufacturer);
  const isCustomInverterModel = Boolean(prefill.inverterModel) && !inverterModels.includes(prefill.inverterModel);
  const isCustomBessManufacturer = Boolean(prefill.bessManufacturer) && !bessManufacturerOptions.includes(prefill.bessManufacturer);
  const isCustomBessModel = Boolean(prefill.bessModel) && !bessModels.includes(prefill.bessModel);
  const selectedModuleSpec = prefill.moduleManufacturer && prefill.moduleModel
    ? getSolarModuleSpec(prefill.moduleManufacturer, prefill.moduleModel)
    : undefined;
  const selectedInverterSpec = prefill.inverterManufacturer && prefill.inverterModel
    ? getSolarInverterSpec(prefill.inverterManufacturer, prefill.inverterModel)
    : undefined;
  const selectedWindSpec = prefill.turbineManufacturer && prefill.turbineModel
    ? getWindSpec(prefill.turbineManufacturer, prefill.turbineModel)
    : undefined;
  const selectedBessSpec = prefill.bessManufacturer && prefill.bessModel
    ? getBessSpec(prefill.bessManufacturer, prefill.bessModel)
    : undefined;
  const inverterCount = Number(form.n_inverters) || 0;
  const unitAcPower = Number(form.inv_ac_kw) || 0;
  const moduleCount = Number(form.n_modules) || 0;
  const moduleWp = Number(form.module_wp) || 0;
  const computedAcCapacity = form.site_type === "wind"
    ? Number(form.cap_ac_kw) || 0
    : inverterCount * unitAcPower;
  const computedDcCapacity = form.site_type === "wind"
    ? Number(form.cap_dc_kwp) || 0
    : (moduleCount * moduleWp) / 1000;
  const computedDcAcRatio = computedAcCapacity > 0 ? computedDcCapacity / computedAcCapacity : 0;
  const showDcAcWarning = form.site_type === "solar" && computedAcCapacity > 0 && computedDcAcRatio > 1.5;
  const retrofitBessContainerCount =
    selectedBessSpec && Number(form.retrofit_bess_energy_kwh) > 0
      ? Math.max(1, Math.ceil((Number(form.retrofit_bess_energy_kwh) / 1000) / selectedBessSpec.energy_mwh))
      : 0;
  const estimatedRetrofitBessLandAreaM2 =
    form.retrofit_bess_enabled && Number(form.retrofit_bess_energy_kwh) > 0
      ? estimateRetrofitBessLandAreaM2(
          Number(form.retrofit_bess_energy_kwh),
          retrofitBessContainerCount,
          selectedBessSpec?.area_with_access_m2
        )
      : 0;

  useEffect(() => {
    if (form.site_type !== "solar") return;
    setInverterCapacities((current) => {
      const targetCount = Math.max(Number(form.n_inverters) || 0, 0);
      if (targetCount === 0) {
        return current;
      }

      if (current.length === targetCount) {
        return current;
      }

      const unitCapacity = (Number(form.cap_dc_kwp) || 0) / Math.max(Number(form.n_inverters) || 1, 1);
      const next = current.slice(0, targetCount);
      while (next.length < targetCount) {
        next.push({
          tag: `INV${next.length + 1}`,
          module_count: Number(form.module_wp) > 0 ? String(Math.round((unitCapacity * 1000) / Number(form.module_wp))) : "",
          dc_capacity_kwp: String(Number(unitCapacity.toFixed(2))),
        });
      }
      return next.map((item, index) => ({
        tag: item.tag || `INV${index + 1}`,
        module_count: item.module_count,
        dc_capacity_kwp:
          item.module_count.trim().length > 0
            ? String(Number((((Number(item.module_count) || 0) * (Number(form.module_wp) || 0)) / 1000).toFixed(2)))
            : item.dc_capacity_kwp.trim().length > 0
              ? item.dc_capacity_kwp
              : String(Number(unitCapacity.toFixed(2))),
      }));
    });
  }, [form.cap_dc_kwp, form.module_wp, form.n_inverters, form.site_type]);

  function updateField<K extends keyof SiteFormState>(key: K, value: SiteFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updatePrefill<K extends keyof PrefillState>(key: K, value: PrefillState[K]) {
    setPrefill((current) => ({ ...current, [key]: value }));
  }

  function composeSolarTechnology(moduleTechnology?: string, solarType?: string) {
    const typeLabel =
      solarType === "rooftop"
        ? "Rooftop"
        : solarType === "floating"
          ? "Floating"
          : solarType === "agri-pv"
            ? "Agri-PV"
            : solarType === "carport"
              ? "Carport"
              : "Ground-mounted";
    return moduleTechnology ? `${typeLabel} (${moduleTechnology})` : typeLabel;
  }

  function applyWindModel(manufacturer: string, model: string) {
    const spec = getWindSpec(manufacturer, model);
    setPrefill((current) => ({ ...current, turbineManufacturer: manufacturer, turbineModel: model }));
    if (!spec) return;
    setForm((current) => ({
      ...current,
      technology: `${manufacturer} ${model}`,
      cap_ac_kw: String(spec.rated_mw * 1000),
      rotor_diameter_m: String(spec.rotor_diameter_m),
    }));
  }

  function applyModuleModel(manufacturer: string, model: string) {
    const spec = getSolarModuleSpec(manufacturer, model);
    setPrefill((current) => ({ ...current, moduleManufacturer: manufacturer, moduleModel: model }));
    if (!spec) return;
    setForm((current) => ({
      ...current,
      technology: composeSolarTechnology(spec.technology, current.solar_type),
      module_brand: manufacturer,
      module_wp: String(spec.power_wp),
    }));
  }

  function applyInverterModel(manufacturer: string, model: string) {
    const spec = getSolarInverterSpec(manufacturer, model);
    setPrefill((current) => ({ ...current, inverterManufacturer: manufacturer, inverterModel: model }));
    if (!spec) return;
    setForm((current) => ({
      ...current,
      inv_model: [manufacturer, model].filter(Boolean).join(" "),
      inv_ac_kw: String(spec.ac_kw),
    }));
  }

  function applyBessModel(manufacturer: string, model: string) {
    const spec = getBessSpec(manufacturer, model);
    setPrefill((current) => ({ ...current, bessManufacturer: manufacturer, bessModel: model }));
    if (!spec) return;
    setForm((current) => ({
      ...current,
      bess_manufacturer: manufacturer,
      bess_model: model,
      bess_power_kw: String(spec.power_mw * 1000),
      bess_energy_kwh: String(spec.energy_mwh * 1000),
      bess_chemistry: spec.chemistry ?? current.bess_chemistry,
      bess_duration_hours: String(spec.duration_hours),
      bess_roundtrip_efficiency_pct:
        spec.round_trip_efficiency_pct != null ? String(spec.round_trip_efficiency_pct) : current.bess_roundtrip_efficiency_pct,
      has_bess: true,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    const resolvedInverterDescriptor =
      form.site_type === "solar"
        ? composeInverterDescriptor(prefill.inverterManufacturer, prefill.inverterModel) || form.inv_model.trim()
        : form.inv_model.trim();
    const resolvedModuleManufacturer = prefill.moduleManufacturer || form.module_brand.trim();
    const resolvedModuleModel = prefill.moduleModel.trim();
    const resolvedBessManufacturer = prefill.bessManufacturer || form.bess_manufacturer.trim();
    const resolvedBessModel = prefill.bessModel || form.bess_model.trim();

    const payload: Record<string, unknown> = {
      display_name: form.display_name,
      country: form.country,
      region: form.region,
      lat: Number(form.lat),
      lon: Number(form.lon),
      cod: toUiDate(form.cod),
      technology: form.technology,
      site_type: form.site_type,
      status: form.status,
      cap_ac_kw: form.site_type === "solar" ? computedAcCapacity : Number(form.cap_ac_kw),
      cap_dc_kwp: form.site_type === "solar" ? computedDcCapacity : Number(form.cap_dc_kwp),
      n_inverters: Number(form.n_inverters),
      inv_ac_kw: Number(form.inv_ac_kw),
      inv_model: resolvedInverterDescriptor,
      n_modules: Number(form.n_modules),
      module_wp: Number(form.module_wp),
      module_brand: form.module_brand,
      site_timezone: form.site_timezone,
      irradiance_basis: form.site_type === "solar" ? form.irradiance_basis || null : null,
      module_tilt_deg: form.site_type === "solar" ? nullableNumber(form.module_tilt_deg) : null,
      tariff_eur_mwh: nullableNumber(form.tariff_eur_mwh),
      has_bess: form.has_bess,
      bess_power_kw: form.has_bess ? nullableNumber(form.bess_power_kw) : null,
      bess_energy_kwh: form.has_bess ? nullableNumber(form.bess_energy_kwh) : null,
      bess_manufacturer: form.has_bess ? resolvedBessManufacturer || null : null,
      bess_model: form.has_bess ? resolvedBessModel || null : null,
      bess_chemistry: form.has_bess ? form.bess_chemistry.trim() || null : null,
      bess_duration_hours: form.has_bess ? nullableNumber(form.bess_duration_hours) : null,
      bess_roundtrip_efficiency_pct: form.has_bess ? nullableNumber(form.bess_roundtrip_efficiency_pct) : null,
      bess_container_count: form.has_bess ? nullableInteger(form.bess_container_count) : null,
      retrofit_bess_enabled: form.retrofit_bess_enabled,
      retrofit_bess_power_kw: form.retrofit_bess_enabled ? nullableNumber(form.retrofit_bess_power_kw) : null,
      retrofit_bess_energy_kwh: form.retrofit_bess_enabled ? nullableNumber(form.retrofit_bess_energy_kwh) : null,
      retrofit_bess_cost_eur_kwh: form.retrofit_bess_enabled ? nullableNumber(form.retrofit_bess_cost_eur_kwh) ?? 200 : null,
      retrofit_bess_land_area_m2: form.retrofit_bess_enabled ? estimatedRetrofitBessLandAreaM2 : null,
      dc_ac_ratio: form.site_type === "solar" ? computedDcAcRatio : Number(form.dc_ac_ratio),
      design_pr: percentStringToDecimal(form.design_pr),
      operating_pr_target: percentStringToDecimal(form.design_pr),
      interval_min: Number(form.interval_min),
      irr_threshold: Number(form.irr_threshold),
      hub_height_m: nullableNumber(form.hub_height_m),
      tip_height_m: nullableNumber(form.tip_height_m),
      rotor_diameter_m: nullableNumber(form.rotor_diameter_m),
      expected_aep_gwh: nullableNumber(form.expected_aep_gwh),
      solar_module_types:
        form.site_type === "solar" && resolvedModuleModel
          ? [
              {
                manufacturer: resolvedModuleManufacturer || null,
                model: resolvedModuleModel,
                module_wp: Number(form.module_wp),
                quantity: Number(form.n_modules),
                technology: selectedModuleSpec?.technology,
                cell_type: selectedModuleSpec?.cell_type,
                module_efficiency_pct: selectedModuleSpec?.module_efficiency_pct,
                bifaciality_pct: selectedModuleSpec?.bifaciality_pct,
                temp_coeff_pmax_pct_per_c: selectedModuleSpec?.temp_coeff_pmax_pct_per_c,
                temp_coeff_voc_pct_per_c: selectedModuleSpec?.temp_coeff_voc_pct_per_c,
                temp_coeff_isc_pct_per_c: selectedModuleSpec?.temp_coeff_isc_pct_per_c,
                first_year_degradation_pct: selectedModuleSpec?.first_year_degradation_pct,
                annual_degradation_pct: selectedModuleSpec?.annual_degradation_pct,
                length_mm: selectedModuleSpec?.length_mm,
                width_mm: selectedModuleSpec?.width_mm,
                thickness_mm: selectedModuleSpec?.thickness_mm,
                weight_kg: selectedModuleSpec?.weight_kg,
                max_system_voltage_v: selectedModuleSpec?.max_system_voltage_v,
                operating_temp_min_c: selectedModuleSpec?.operating_temp_min_c,
                operating_temp_max_c: selectedModuleSpec?.operating_temp_max_c,
                glass_description: selectedModuleSpec?.glass_description,
                frame_description: selectedModuleSpec?.frame_description,
                source_url: selectedModuleSpec?.source_url,
              },
            ]
          : [],
      solar_inverter_units:
        form.site_type === "solar"
          ? inverterCapacities
              .map((item) => ({
                tag: item.tag.trim(),
                module_count: item.module_count.trim().length > 0 ? Number(item.module_count) : null,
                dc_capacity_kwp: parseDecimalDraft(item.dc_capacity_kwp),
              }))
              .filter((item) => item.tag.length > 0)
          : [],
    };

    try {
      const saved = isNewSite ? await api.sites.create(payload) : await api.sites.update(params.siteId, payload);
      await mutate(["site", saved.id], saved, false);
      await mutate(["site", saved.id]);
      await mutate(["sites"]);
      router.push(`/dashboard/site/${saved.id}`);
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save site");
    } finally {
      setSaving(false);
    }
  }

  function updateInverterCapacity(index: number, patch: Partial<InverterCapacityDraft>) {
    setInverterCapacities((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item))
    );
  }

  async function handleDelete() {
    if (isNewSite || deleting) return;
    const confirmed = window.confirm(`Delete site "${form.display_name}"? This cannot be undone.`);
    if (!confirmed) return;

    setDeleting(true);
    setError(null);
    try {
      await api.sites.delete(params.siteId);
      router.push("/dashboard");
      router.refresh();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Failed to delete site");
      setDeleting(false);
    }
  }

  if (!isNewSite && isLoading) {
    return <p className="text-sm text-slate-400">{t("common.loading")}</p>;
  }

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/site-edit-hero.jpg" alt="Site edit hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(110deg,rgba(2,14,22,0.94),rgba(4,24,38,0.82),rgba(4,24,38,0.72))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href={backHref} label={backLabel} />

        <div className="space-y-2">
          <h1 className="font-dolfines text-2xl font-semibold tracking-[0.08em] text-white">
            {isNewSite ? t("common.createSite") : t("common.editSite")}
          </h1>
          <p className="text-sm text-slate-300">
            {isNewSite ? "Create a new site record for REVEAL reporting." : "Update site details used for reporting and analysis."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
        <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
          {sectionTitle("General")}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Name</span>
              <input className={fieldClassName()} value={form.display_name} onFocus={selectAllOnFocus} onChange={(e) => updateField("display_name", e.target.value)} required />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Site type</span>
              <select className={fieldClassName()} value={form.site_type} onChange={(e) => updateField("site_type", e.target.value as SiteType)}>
                <option value="solar">Solar PV</option>
                <option value="wind">Wind</option>
              </select>
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Status</span>
              <select className={fieldClassName()} value={form.status} onChange={(e) => updateField("status", e.target.value as SiteStatus)}>
                <option value="operational">Operational</option>
                <option value="maintenance">Maintenance</option>
                <option value="offline">Offline</option>
              </select>
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Country</span>
              <SuggestionField
                value={form.country}
                onChange={(value) => updateField("country", value)}
                suggestions={COUNTRY_SUGGESTIONS}
                placeholder="Start typing a country"
                required
              />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Region</span>
              <SuggestionField
                value={form.region}
                onChange={(value) => updateField("region", value)}
                suggestions={regionSuggestions}
                placeholder={regionSuggestions.length ? "Start typing a region" : "Enter region"}
                required
              />
            </label>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300 md:col-span-2">
              <p className="font-semibold text-white">Site location and GPS coordinates</p>
              <p className="mt-1">
                Enter the site latitude and longitude here. REVEAL uses these saved GPS coordinates to place the site on the map and to support weather-context features.
              </p>
            </div>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Latitude</span>
              <span className="block text-xs text-slate-400">Decimal degrees, for example `46.2276`</span>
                <input
                  className={fieldClassName()}
                  type="text"
                  {...decimalInputProps()}
                  value={form.lat}
                  onChange={(e) => updateField("lat", normalizeDecimalInput(e.target.value))}
                  placeholder="46.2276"
                  required
                />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Longitude</span>
              <span className="block text-xs text-slate-400">Decimal degrees, for example `2.2137`</span>
                <input
                  className={fieldClassName()}
                  type="text"
                  {...decimalInputProps()}
                  value={form.lon}
                  onChange={(e) => updateField("lon", normalizeDecimalInput(e.target.value))}
                  placeholder="2.2137"
                  required
                />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">COD</span>
              <input className={fieldClassName()} type="date" onFocus={selectAllOnFocus} value={form.cod} onChange={(e) => updateField("cod", e.target.value)} required />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Site timezone</span>
              <input className={fieldClassName()} value={form.site_timezone} onFocus={selectAllOnFocus} onChange={(e) => updateField("site_timezone", e.target.value)} required />
              {inferTimezone(form.country, form.region) ? (
                <span className="block text-xs text-slate-400">
                  Suggested from location: {inferTimezone(form.country, form.region)}
                </span>
              ) : null}
            </label>
          </div>
        </section>

        {form.site_type === "solar" ? (
          <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
            {sectionTitle("Solar Equipment Knowledge Base")}
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Solar type</span>
                <select
                  className={fieldClassName()}
                  value={form.solar_type}
                  onChange={(e) =>
                    setForm((current) => ({
                      ...current,
                      solar_type: e.target.value,
                      technology: composeSolarTechnology(
                        prefill.moduleManufacturer && prefill.moduleModel
                          ? getSolarModuleSpec(prefill.moduleManufacturer, prefill.moduleModel)?.technology
                          : current.technology.replace(/^[^(]+ \((.*)\)$/, "$1"),
                        e.target.value
                      ),
                    }))
                  }
                >
                  <option value="ground-mounted">Ground mounted</option>
                  <option value="rooftop">Rooftop</option>
                  <option value="floating">Floating</option>
                  <option value="agri-pv">Agri-PV</option>
                  <option value="carport">Carport</option>
                </select>
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Module manufacturer</span>
                <select
                  className={fieldClassName()}
                  value={isCustomModuleManufacturer ? OTHER_OPTION : prefill.moduleManufacturer}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("moduleManufacturer", "");
                      updatePrefill("moduleModel", "");
                      updateField("module_brand", "");
                      return;
                    }
                    updatePrefill("moduleManufacturer", e.target.value);
                    updatePrefill("moduleModel", "");
                    updateField("module_brand", e.target.value);
                  }}
                >
                  <option value="">Select manufacturer</option>
                  {moduleManufacturers.map((manufacturer) => (
                    <option key={manufacturer} value={manufacturer}>{manufacturer}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomModuleManufacturer || !prefill.moduleManufacturer) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.moduleManufacturer}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => {
                      updatePrefill("moduleManufacturer", e.target.value);
                      updateField("module_brand", e.target.value);
                    }}
                    placeholder="Enter module manufacturer"
                  />
                )}
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Module model</span>
                <select
                  className={fieldClassName()}
                  value={isCustomModuleModel ? OTHER_OPTION : prefill.moduleModel}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("moduleModel", "");
                      return;
                    }
                    applyModuleModel(prefill.moduleManufacturer, e.target.value);
                  }}
                  disabled={!prefill.moduleManufacturer}
                >
                  <option value="">Select module</option>
                  {moduleModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomModuleModel || !prefill.moduleModel) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.moduleModel}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => updatePrefill("moduleModel", e.target.value)}
                    placeholder="Enter module model"
                    disabled={!prefill.moduleManufacturer}
                  />
                )}
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Inverter manufacturer</span>
                <select
                  className={fieldClassName()}
                  value={isCustomInverterManufacturer ? OTHER_OPTION : prefill.inverterManufacturer}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("inverterManufacturer", "");
                      updatePrefill("inverterModel", "");
                      updateField("inv_model", "");
                      return;
                    }
                    updatePrefill("inverterManufacturer", e.target.value);
                    updatePrefill("inverterModel", "");
                    if (!prefill.inverterModel) {
                      updateField("inv_model", e.target.value);
                    }
                  }}
                >
                  <option value="">Select manufacturer</option>
                  {inverterManufacturers.map((manufacturer) => (
                    <option key={manufacturer} value={manufacturer}>{manufacturer}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomInverterManufacturer || !prefill.inverterManufacturer) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.inverterManufacturer}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => {
                      updatePrefill("inverterManufacturer", e.target.value);
                      updateField("inv_model", composeInverterDescriptor(e.target.value, prefill.inverterModel));
                    }}
                    placeholder="Enter inverter manufacturer"
                  />
                )}
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Inverter model</span>
                <select
                  className={fieldClassName()}
                  value={isCustomInverterModel ? OTHER_OPTION : prefill.inverterModel}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("inverterModel", "");
                      updateField("inv_model", composeInverterDescriptor(prefill.inverterManufacturer, ""));
                      return;
                    }
                    applyInverterModel(prefill.inverterManufacturer, e.target.value);
                  }}
                  disabled={!prefill.inverterManufacturer}
                >
                  <option value="">Select inverter</option>
                  {inverterModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomInverterModel || !prefill.inverterModel) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.inverterModel}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => {
                      updatePrefill("inverterModel", e.target.value);
                      updateField("inv_model", composeInverterDescriptor(prefill.inverterManufacturer, e.target.value));
                    }}
                    placeholder="Enter inverter model"
                    disabled={!prefill.inverterManufacturer}
                  />
                )}
              </label>
            </div>
            {selectedModuleSpec ? (
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Module datasheet</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedModuleSpec.power_wp} Wp · {selectedModuleSpec.module_efficiency_pct ?? "—"}% eff.</p>
                  <p className="mt-1 text-xs text-slate-300">{selectedModuleSpec.technology}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Degradation</p>
                  <p className="mt-2 text-sm font-semibold text-white">
                    Y1 {selectedModuleSpec.first_year_degradation_pct ?? "—"}% · Annual {selectedModuleSpec.annual_degradation_pct ?? "—"}%
                  </p>
                  <p className="mt-1 text-xs text-slate-300">Useful for long-term expected-yield assumptions.</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Temperature behaviour</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedModuleSpec.temp_coeff_pmax_pct_per_c ?? "—"}%/°C Pmax</p>
                  <p className="mt-1 text-xs text-slate-300">Voc {selectedModuleSpec.temp_coeff_voc_pct_per_c ?? "—"}%/°C · Isc {selectedModuleSpec.temp_coeff_isc_pct_per_c ?? "—"}%/°C</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Mechanical</p>
                  <p className="mt-2 text-sm font-semibold text-white">
                    {selectedModuleSpec.length_mm ?? "—"} × {selectedModuleSpec.width_mm ?? "—"} mm
                  </p>
                  <p className="mt-1 text-xs text-slate-300">
                    {selectedModuleSpec.weight_kg ?? "—"} kg · {selectedModuleSpec.max_system_voltage_v ?? "—"} V max system
                  </p>
                </div>
              </div>
            ) : null}
            {selectedInverterSpec ? (
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Inverter datasheet</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedInverterSpec.ac_kw} kW AC</p>
                  <p className="mt-1 text-xs text-slate-300">Max eff. {selectedInverterSpec.max_efficiency_pct ?? "—"}% · EU {selectedInverterSpec.european_efficiency_pct ?? "—"}%</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">DC architecture</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedInverterSpec.max_dc_voltage_v ?? "—"} V max DC</p>
                  <p className="mt-1 text-xs text-slate-300">{selectedInverterSpec.mppt_count ?? "—"} MPPT · Start {selectedInverterSpec.startup_voltage_v ?? "—"} V</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Operating window</p>
                  <p className="mt-2 text-sm font-semibold text-white">
                    {selectedInverterSpec.operating_temp_min_c ?? "—"} to {selectedInverterSpec.operating_temp_max_c ?? "—"} °C
                  </p>
                  <p className="mt-1 text-xs text-slate-300">{selectedInverterSpec.protection_rating ?? "Protection N/A"}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Communications</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedInverterSpec.communication ?? "N/A"}</p>
                </div>
              </div>
            ) : null}
          </section>
        ) : (
          <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
            {sectionTitle("Wind Equipment Knowledge Base")}
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Turbine manufacturer</span>
                <select
                  className={fieldClassName()}
                  value={isCustomWindManufacturer ? OTHER_OPTION : prefill.turbineManufacturer}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("turbineManufacturer", "");
                      updatePrefill("turbineModel", "");
                      updateField("technology", "");
                      return;
                    }
                    updatePrefill("turbineManufacturer", e.target.value);
                    updatePrefill("turbineModel", "");
                  }}
                >
                  <option value="">Select manufacturer</option>
                  {windManufacturers.map((manufacturer) => (
                    <option key={manufacturer} value={manufacturer}>{manufacturer}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomWindManufacturer || !prefill.turbineManufacturer) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.turbineManufacturer}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => {
                      updatePrefill("turbineManufacturer", e.target.value);
                      updateField("technology", composeInverterDescriptor(e.target.value, prefill.turbineModel));
                    }}
                    placeholder="Enter turbine manufacturer"
                  />
                )}
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Turbine model</span>
                <select
                  className={fieldClassName()}
                  value={isCustomWindModel ? OTHER_OPTION : prefill.turbineModel}
                  onChange={(e) => {
                    if (e.target.value === OTHER_OPTION) {
                      updatePrefill("turbineModel", "");
                      updateField("technology", composeInverterDescriptor(prefill.turbineManufacturer, ""));
                      return;
                    }
                    applyWindModel(prefill.turbineManufacturer, e.target.value);
                  }}
                  disabled={!prefill.turbineManufacturer}
                >
                  <option value="">Select turbine</option>
                  {windModels.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                  <option value={OTHER_OPTION}>Other</option>
                </select>
                {(isCustomWindModel || !prefill.turbineModel) && (
                  <input
                    className={fieldClassName()}
                    value={prefill.turbineModel}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => {
                      updatePrefill("turbineModel", e.target.value);
                      updateField("technology", composeInverterDescriptor(prefill.turbineManufacturer, e.target.value));
                    }}
                    placeholder="Enter turbine model"
                    disabled={!prefill.turbineManufacturer}
                  />
                )}
              </label>
            </div>
            {selectedWindSpec ? (
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Turbine datasheet</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedWindSpec.rated_mw} MW rated</p>
                  <p className="mt-1 text-xs text-slate-300">{selectedWindSpec.rotor_diameter_m} m rotor · {selectedWindSpec.swept_area_m2?.toLocaleString() ?? "—"} m2 swept area</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Wind class</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedWindSpec.iec_class ?? "—"}</p>
                  <p className="mt-1 text-xs text-slate-300">Hub height range {selectedWindSpec.hub_height_range_m ?? "—"} m</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Power curve markers</p>
                  <p className="mt-2 text-sm font-semibold text-white">
                    Cut-in {selectedWindSpec.cut_in_ws_ms ?? "—"} m/s · Rated {selectedWindSpec.rated_ws_ms ?? "—"} m/s
                  </p>
                  <p className="mt-1 text-xs text-slate-300">Cut-out {selectedWindSpec.cut_out_ws_ms ?? "—"} m/s</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Drive train</p>
                  <p className="mt-2 text-sm font-semibold text-white">{selectedWindSpec.drivetrain ?? "—"}</p>
                  <p className="mt-1 text-xs text-slate-300">{selectedWindSpec.generator ?? "Generator N/A"}</p>
                </div>
              </div>
            ) : null}
          </section>
        )}

        <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
          {sectionTitle("Performance and Configuration")}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Inverters / turbines</span>
                <input className={fieldClassName()} type="number" {...integerInputProps()} value={form.n_inverters} onChange={(e) => updateField("n_inverters", e.target.value)} />
            </label>
            {form.site_type === "solar" ? (
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Modules</span>
                <input className={fieldClassName()} type="number" {...integerInputProps()} value={form.n_modules} onChange={(e) => updateField("n_modules", e.target.value)} />
              </label>
            ) : (
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">AC capacity (kW)</span>
                <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.cap_ac_kw} onChange={(e) => updateField("cap_ac_kw", normalizeDecimalInput(e.target.value))} />
              </label>
            )}
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Unit AC power (kW)</span>
              <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.inv_ac_kw} onChange={(e) => updateField("inv_ac_kw", normalizeDecimalInput(e.target.value))} />
            </label>
            {form.site_type === "solar" ? (
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Module Wp</span>
                <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.module_wp} onChange={(e) => updateField("module_wp", normalizeDecimalInput(e.target.value))} />
              </label>
            ) : (
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">DC capacity (kWp)</span>
                <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.cap_dc_kwp} onChange={(e) => updateField("cap_dc_kwp", normalizeDecimalInput(e.target.value))} />
              </label>
            )}
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Inverter model</span>
              <input className={fieldClassName()} value={form.inv_model} onFocus={selectAllOnFocus} onChange={(e) => updateField("inv_model", e.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Design PR (%)</span>
              <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.design_pr} onChange={(e) => updateField("design_pr", normalizeDecimalInput(e.target.value))} />
              <span className="text-xs text-slate-400">
                Enter a percentage such as 80. REVEAL converts it internally to a decimal and degrades it automatically by 0.5% per year from COD.
              </span>
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">SCADA interval (min)</span>
              <input className={fieldClassName()} type="number" {...integerInputProps()} value={form.interval_min} onChange={(e) => updateField("interval_min", e.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
          <span className="font-semibold text-white">Irradiance threshold (W/m2)</span>
              <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.irr_threshold} onChange={(e) => updateField("irr_threshold", normalizeDecimalInput(e.target.value))} />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Site tariff (EUR/MWh)</span>
              <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.tariff_eur_mwh} onChange={(e) => updateField("tariff_eur_mwh", normalizeDecimalInput(e.target.value))} />
            </label>
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">Battery storage present</span>
              <select
                className={fieldClassName()}
                value={form.has_bess ? "yes" : "no"}
                onChange={(e) => updateField("has_bess", e.target.value === "yes")}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
            {form.has_bess ? (
              <>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">BESS manufacturer</span>
                  <select
                    className={fieldClassName()}
                    value={isCustomBessManufacturer ? OTHER_OPTION : prefill.bessManufacturer}
                    onChange={(e) => {
                      if (e.target.value === OTHER_OPTION) {
                        updatePrefill("bessManufacturer", "");
                        updatePrefill("bessModel", "");
                        updateField("bess_manufacturer", "");
                        updateField("bess_model", "");
                        return;
                      }
                      updatePrefill("bessManufacturer", e.target.value);
                      updatePrefill("bessModel", "");
                      updateField("bess_manufacturer", e.target.value);
                      updateField("bess_model", "");
                    }}
                  >
                    <option value="">Select manufacturer</option>
                    {bessManufacturers.map((manufacturer) => (
                      <option key={manufacturer} value={manufacturer}>{manufacturer}</option>
                    ))}
                    <option value={OTHER_OPTION}>Other</option>
                  </select>
                  {(isCustomBessManufacturer || !prefill.bessManufacturer) && (
                    <input
                      className={fieldClassName()}
                      value={prefill.bessManufacturer || form.bess_manufacturer}
                      onFocus={selectAllOnFocus}
                      onChange={(e) => {
                        updatePrefill("bessManufacturer", e.target.value);
                        updatePrefill("bessModel", "");
                        updateField("bess_manufacturer", e.target.value);
                        updateField("bess_model", "");
                      }}
                      placeholder="Enter BESS manufacturer"
                    />
                  )}
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">BESS container / model</span>
                  <select
                    className={fieldClassName()}
                    value={isCustomBessModel ? OTHER_OPTION : prefill.bessModel}
                    onChange={(e) => {
                      if (e.target.value === OTHER_OPTION) {
                        updatePrefill("bessModel", "");
                        updateField("bess_model", "");
                        return;
                      }
                      applyBessModel(prefill.bessManufacturer, e.target.value);
                    }}
                    disabled={!prefill.bessManufacturer}
                  >
                    <option value="">Select model</option>
                    {bessModels.map((model) => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                    <option value={OTHER_OPTION}>Other</option>
                  </select>
                  {(isCustomBessModel || !prefill.bessModel) && (
                    <input
                      className={fieldClassName()}
                      value={prefill.bessModel || form.bess_model}
                      onFocus={selectAllOnFocus}
                      onChange={(e) => {
                        updatePrefill("bessModel", e.target.value);
                        updateField("bess_model", e.target.value);
                      }}
                      placeholder="Enter BESS model"
                      disabled={!prefill.bessManufacturer && !form.bess_manufacturer}
                    />
                  )}
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">BESS continuous power (kW)</span>
                  <input
                    className={fieldClassName()}
                    type="text"
                    {...decimalInputProps()}
                    value={form.bess_power_kw}
                    onChange={(e) => updateField("bess_power_kw", normalizeDecimalInput(e.target.value))}
                  />
                  <span className="text-xs text-slate-400">Use the rated continuous charge or discharge power, not a short observed operating range.</span>
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">BESS usable energy (kWh)</span>
                  <input
                    className={fieldClassName()}
                    type="text"
                    {...decimalInputProps()}
                    value={form.bess_energy_kwh}
                    onChange={(e) => updateField("bess_energy_kwh", normalizeDecimalInput(e.target.value))}
                  />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">Chemistry</span>
                  <input
                    className={fieldClassName()}
                    value={form.bess_chemistry}
                    onFocus={selectAllOnFocus}
                    onChange={(e) => updateField("bess_chemistry", e.target.value)}
                    placeholder="LFP, NMC, sodium-ion..."
                  />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">Duration (h)</span>
                  <input
                    className={fieldClassName()}
                    type="text"
                    {...decimalInputProps()}
                    value={form.bess_duration_hours}
                    onChange={(e) => updateField("bess_duration_hours", normalizeDecimalInput(e.target.value))}
                  />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">Round-trip efficiency (%)</span>
                  <input
                    className={fieldClassName()}
                    type="text"
                    {...decimalInputProps()}
                    value={form.bess_roundtrip_efficiency_pct}
                    onChange={(e) => updateField("bess_roundtrip_efficiency_pct", normalizeDecimalInput(e.target.value))}
                  />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">Container count</span>
                  <input
                    className={fieldClassName()}
                    type="number"
                    {...integerInputProps()}
                    value={form.bess_container_count}
                    onChange={(e) => updateField("bess_container_count", e.target.value)}
                  />
                </label>
                <label className="space-y-1 text-sm text-slate-300 md:col-span-2">
                  <span className="font-semibold text-white">Retrofit BESS candidate</span>
                  <select
                    className={fieldClassName()}
                    value={form.retrofit_bess_enabled ? "yes" : "no"}
                    onChange={(e) => updateField("retrofit_bess_enabled", e.target.value === "yes")}
                  >
                    <option value="no">No retrofit case yet</option>
                    <option value="yes">Yes, evaluate retrofit case</option>
                  </select>
                  <span className="text-xs text-slate-400">
                    Keep the installed BESS data above for the actual site, and use this section for a separate retrofit screening case.
                  </span>
                </label>
                {form.retrofit_bess_enabled ? (
                  <>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="font-semibold text-white">Retrofit BESS power (kW)</span>
                      <input
                        className={fieldClassName()}
                        type="text"
                        {...decimalInputProps()}
                        value={form.retrofit_bess_power_kw}
                        onChange={(e) => updateField("retrofit_bess_power_kw", normalizeDecimalInput(e.target.value))}
                      />
                    </label>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="font-semibold text-white">Retrofit BESS energy (kWh)</span>
                      <input
                        className={fieldClassName()}
                        type="text"
                        {...decimalInputProps()}
                        value={form.retrofit_bess_energy_kwh}
                        onChange={(e) => updateField("retrofit_bess_energy_kwh", normalizeDecimalInput(e.target.value))}
                      />
                    </label>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="font-semibold text-white">Retrofit capex placeholder (EUR/kWh)</span>
                      <input
                        className={fieldClassName()}
                        type="text"
                        {...decimalInputProps()}
                        value={form.retrofit_bess_cost_eur_kwh}
                        onChange={(e) => updateField("retrofit_bess_cost_eur_kwh", normalizeDecimalInput(e.target.value))}
                      />
                      <span className="text-xs text-slate-400">Default value set to EUR 200/kWh until project-specific pricing is entered.</span>
                    </label>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="font-semibold text-white">Estimated land area required (m2)</span>
                      <input
                        className={fieldClassName()}
                        type="text"
                        {...decimalInputProps()}
                        value={estimatedRetrofitBessLandAreaM2 > 0 ? String(estimatedRetrofitBessLandAreaM2) : form.retrofit_bess_land_area_m2}
                        readOnly
                      />
                      <span className="text-xs text-slate-400">
                        Includes a layout allowance for access aisles. If a known container is selected, REVEAL uses its indicative installed area; otherwise it falls back to 30 m2/MWh.
                      </span>
                    </label>
                  </>
                ) : null}
              </>
            ) : null}
            <label className="space-y-1 text-sm text-slate-300">
              <span className="font-semibold text-white">DC/AC ratio</span>
              <input
                className={fieldClassName()}
                type="text"
                {...decimalInputProps()}
                value={form.site_type === "solar" ? computedDcAcRatio.toFixed(3) : form.dc_ac_ratio}
                onChange={(e) => updateField("dc_ac_ratio", normalizeDecimalInput(e.target.value))}
                readOnly={form.site_type === "solar"}
              />
            </label>
            {form.site_type === "solar" ? (
              <>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">AC capacity (kW)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={computedAcCapacity.toFixed(2)} readOnly />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">DC capacity (kWp)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={computedDcCapacity.toFixed(2)} readOnly />
                </label>
              </>
            ) : (
              <>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">AC capacity (kW)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.cap_ac_kw} onChange={(e) => updateField("cap_ac_kw", normalizeDecimalInput(e.target.value))} />
                </label>
                <label className="space-y-1 text-sm text-slate-300">
                  <span className="font-semibold text-white">DC capacity (kWp)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.cap_dc_kwp} onChange={(e) => updateField("cap_dc_kwp", normalizeDecimalInput(e.target.value))} />
                </label>
              </>
            )}
          </div>
          {showDcAcWarning ? (
            <div className="rounded-2xl border border-orange-DEFAULT/50 bg-orange-DEFAULT/10 px-4 py-3 text-sm text-orange-100">
              <p className="font-semibold text-orange-200">DC/AC ratio warning</p>
              <p className="mt-1">
                The calculated DC/AC ratio is <span className="font-semibold">{computedDcAcRatio.toFixed(3)}</span>, which is above 1.5.
                This may indicate an incorrect module count, module power, inverter quantity, or inverter AC rating.
              </p>
            </div>
          ) : null}
          {form.has_bess && selectedBessSpec ? (
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">BESS datasheet</p>
                <p className="mt-2 text-sm font-semibold text-white">
                  {selectedBessSpec.power_mw} MW / {selectedBessSpec.energy_mwh} MWh
                </p>
                <p className="mt-1 text-xs text-slate-300">{selectedBessSpec.duration_hours} h duration</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Cell chemistry</p>
                <p className="mt-2 text-sm font-semibold text-white">{selectedBessSpec.chemistry ?? "—"}</p>
                <p className="mt-1 text-xs text-slate-300">
                  RTE {selectedBessSpec.round_trip_efficiency_pct ?? "—"}%
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Cooling and enclosure</p>
                <p className="mt-2 text-sm font-semibold text-white">{selectedBessSpec.cooling ?? "—"}</p>
                <p className="mt-1 text-xs text-slate-300">{selectedBessSpec.enclosure_rating ?? "Enclosure N/A"}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Safety and life</p>
                <p className="mt-2 text-sm font-semibold text-white">{selectedBessSpec.cycle_life ?? "—"}</p>
                <p className="mt-1 text-xs text-slate-300">{selectedBessSpec.fire_suppression ?? "Safety system N/A"}</p>
              </div>
            </div>
          ) : null}
        </section>

        {form.site_type === "solar" ? (
          <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
            {sectionTitle("Per-inverter DC capacities")}
            <p className="text-sm text-slate-300">
              Define the DC capacity inverter by inverter so REVEAL can later chart raw inverter power as well as inverter-specific yield in kWh/kWp in the Charting workspace.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {inverterCapacities.map((item, index) => (
                <div key={`inv-cap-${index}`} className="rounded-2xl border border-white/8 bg-white/5 px-2.5 pb-1 pt-2">
                  <div className="grid gap-1.5 md:grid-cols-3">
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="text-xs font-semibold text-white">Inverter tag</span>
                      <input
                        className={fieldClassName()}
                        value={item.tag}
                        onFocus={selectAllOnFocus}
                          onChange={(e) => updateInverterCapacity(index, { tag: e.target.value })}
                          placeholder={`INV${index + 1}`}
                        />
                    </label>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="text-xs font-semibold text-white"># Modules</span>
                      <input
                        className={fieldClassName()}
                        type="number"
                        {...integerInputProps()}
                        value={item.module_count}
                        onChange={(e) => updateInverterCapacity(index, { module_count: e.target.value })}
                      />
                    </label>
                    <label className="space-y-1 text-sm text-slate-300">
                      <span className="text-xs font-semibold text-white">DC capacity (kWp)</span>
                      <input
                        className={fieldClassName()}
                        type="text"
                        inputMode="decimal"
                        onFocus={selectAllOnFocus}
                        value={item.module_count.trim().length > 0 ? String(Number((((Number(item.module_count) || 0) * (Number(form.module_wp) || 0)) / 1000).toFixed(2))) : item.dc_capacity_kwp}
                        readOnly
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {form.site_type === "solar" ? (
          <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
            {sectionTitle("Solar Site Details")}
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-300 md:col-span-2">
                <span className="font-semibold text-white">Technology</span>
                <input className={fieldClassName()} value={form.technology} onFocus={selectAllOnFocus} readOnly />
              </label>
              <label className="space-y-1 text-sm text-slate-300 md:col-span-2">
                <span className="font-semibold text-white">Module brand</span>
                <input className={fieldClassName()} value={form.module_brand} onFocus={selectAllOnFocus} onChange={(e) => updateField("module_brand", e.target.value)} />
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Module tilt (deg)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.module_tilt_deg} onChange={(e) => updateField("module_tilt_deg", normalizeDecimalInput(e.target.value))} />
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Irradiance basis</span>
                <select className={fieldClassName()} value={form.irradiance_basis} onChange={(e) => updateField("irradiance_basis", e.target.value)}>
                  <option value="poa">POA</option>
                  <option value="ghi">GHI</option>
                </select>
              </label>
            </div>
          </section>
        ) : (
          <section className="space-y-4 rounded-3xl border border-navy-light bg-navy-DEFAULT/70 p-6">
            {sectionTitle("Wind Site Details")}
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Hub height (m)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.hub_height_m} onChange={(e) => updateField("hub_height_m", normalizeDecimalInput(e.target.value))} />
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Tip height (m)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.tip_height_m} onChange={(e) => updateField("tip_height_m", normalizeDecimalInput(e.target.value))} />
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Rotor diameter (m)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.rotor_diameter_m} onChange={(e) => updateField("rotor_diameter_m", normalizeDecimalInput(e.target.value))} />
              </label>
              <label className="space-y-1 text-sm text-slate-300">
                <span className="font-semibold text-white">Expected AEP (GWh)</span>
                  <input className={fieldClassName()} type="text" {...decimalInputProps()} value={form.expected_aep_gwh} onChange={(e) => updateField("expected_aep_gwh", normalizeDecimalInput(e.target.value))} />
              </label>
            </div>
          </section>
        )}

        {error && <p className="text-sm font-semibold text-danger">{error}</p>}

        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" loading={saving}>
            {saving ? t("common.saving") : t("common.save")}
          </Button>
          <Button type="button" variant="ghost" onClick={() => router.push(backHref)}>
            {t("common.cancel")}
          </Button>
          {!isNewSite ? (
            <Button type="button" variant="ghost" className="border border-danger/40 text-danger hover:bg-danger/10" onClick={handleDelete} loading={deleting}>
              Delete site
            </Button>
          ) : null}
        </div>
        </form>
      </div>
    </div>
  );
}
