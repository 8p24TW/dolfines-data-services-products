ALTER TABLE "Site"
ADD COLUMN "bess_manufacturer" TEXT,
ADD COLUMN "bess_model" TEXT,
ADD COLUMN "bess_chemistry" TEXT,
ADD COLUMN "bess_duration_hours" DOUBLE PRECISION,
ADD COLUMN "bess_roundtrip_efficiency_pct" DOUBLE PRECISION,
ADD COLUMN "bess_container_count" INTEGER;

ALTER TABLE "SolarModuleType"
ADD COLUMN "technology" TEXT,
ADD COLUMN "cell_type" TEXT,
ADD COLUMN "module_efficiency_pct" DOUBLE PRECISION,
ADD COLUMN "bifaciality_pct" DOUBLE PRECISION,
ADD COLUMN "temp_coeff_pmax_pct_per_c" DOUBLE PRECISION,
ADD COLUMN "temp_coeff_voc_pct_per_c" DOUBLE PRECISION,
ADD COLUMN "temp_coeff_isc_pct_per_c" DOUBLE PRECISION,
ADD COLUMN "first_year_degradation_pct" DOUBLE PRECISION,
ADD COLUMN "annual_degradation_pct" DOUBLE PRECISION,
ADD COLUMN "length_mm" DOUBLE PRECISION,
ADD COLUMN "width_mm" DOUBLE PRECISION,
ADD COLUMN "thickness_mm" DOUBLE PRECISION,
ADD COLUMN "weight_kg" DOUBLE PRECISION,
ADD COLUMN "max_system_voltage_v" DOUBLE PRECISION,
ADD COLUMN "operating_temp_min_c" DOUBLE PRECISION,
ADD COLUMN "operating_temp_max_c" DOUBLE PRECISION,
ADD COLUMN "glass_description" TEXT,
ADD COLUMN "frame_description" TEXT,
ADD COLUMN "source_url" TEXT;
