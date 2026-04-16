# REPAT Methodology

## Long-Term Resource Normalization, Synthetic Hourly Modelling, and BESS Assessment

### Version
Draft 1.0

### Language
English

### Purpose
This document describes the proposed technical methodology behind two major REPAT platform extensions:

1. Long-term hourly time-series generation for solar and wind assets
2. Standalone Battery Energy Storage System (BESS) performance analysis

The objective is to provide a transparent, technically credible framework that can be presented to clients, auditors, and internal reviewers. The methodology is designed to support engineering studies, retrofit screening, operational benchmarking, storage sizing, and investment-grade analysis workflows.

---

## 1. Scope

REPAT currently supports operational analysis and reporting for solar PV and wind assets. The next development phase extends the platform in two directions:

1. Creation of long-term synthetic hourly data sets for modelling purposes
2. Integration of standalone BESS systems as a new asset class with dedicated analytics

These two workstreams are linked. A reliable long-term hourly generation model is a core input to future BESS retrofit and storage sizing studies.

---

## 2. Guiding Principles

The methodology is based on the following principles:

- Use measured site data whenever available
- Anchor long-term modelling in recognized external reference data sets
- Separate resource normalization from plant performance normalization
- Preserve hourly and seasonal behavior rather than relying only on annual averages
- Exclude or flag non-representative operational periods where possible
- Maintain a clear audit trail from raw input to final model output
- Prefer conservative assumptions when data quality is uncertain

---

## 3. Phase 1: Long-Term Hourly Modelling for Solar Sites

### 3.1 Objective

The objective is to generate a long-term hourly CSV representing the expected operational behavior of a solar plant under normalized long-term irradiance conditions. The output should be suitable for:

- BESS retrofit screening
- Curtailment recovery assessment
- Revenue and dispatch modelling
- Long-term performance benchmarking
- Repowering and augmentation studies

### 3.2 Core Concept

The methodology combines:

- Measured site irradiance and power
- Long-term reference irradiance data at the site location
- Observed plant performance behavior

The final hourly series is not a simple copy of measured SCADA. It is a normalized synthetic time series based on long-term meteorological conditions and site-calibrated plant response.

### 3.3 Required Inputs

#### Mandatory Inputs

- Site coordinates
- Site timezone
- Installed DC capacity
- Installed AC capacity
- SCADA interval
- At least one SCADA file containing:
  - timestamp
  - site power or summed inverter/junction-box power
  - site irradiance

#### Strongly Recommended Inputs

- Six to twelve months of SCADA data
- Module type and technology
- Inverter configuration
- Known outage periods
- Known curtailment periods
- Plant PR target or expected specific yield

#### Optional Inputs

- Module temperature
- Ambient temperature
- Tracker status
- Soiling observations
- Grid export limitation information

### 3.4 External Reference Data

The primary proposed reference source is:

- ERA5-Land hourly reanalysis data

The secondary reference or validation sources may include:

- ERA5
- NASA POWER
- Satellite-derived irradiance products where appropriate

#### Reference Variables for Solar

- Surface solar radiation downwards
- Optional ambient temperature
- Optional wind speed for module temperature adjustments

### 3.5 Methodology Steps

#### Step 1: Data Ingestion

Measured SCADA data are loaded and standardized. The platform identifies:

- time series coverage
- missing values
- irradiance source
- power channels
- daylight windows

#### Step 2: Data Quality Screening

The SCADA data set is screened to identify:

- missing or duplicated timestamps
- flatlined sensors
- irradiance sensor anomalies
- periods with outages
- clipping periods
- curtailment periods
- non-physical values

Periods that are not representative of normal plant behavior are excluded from correlation and normalization steps or are explicitly flagged.

#### Step 3: Site-to-Reference Correlation

Measured site irradiance is compared against the long-term reference irradiance at the same location over the overlapping period.

This step is used to estimate:

- bias between site sensor and reference source
- seasonal behavior differences
- persistence of under- or over-estimation
- confidence in the reference data for this site

The result is a correction relationship between reference irradiance and site-observed irradiance.

#### Step 4: Plant Performance Normalization

Measured plant output is related to measured irradiance to characterize actual plant performance. This step seeks to isolate the operational behavior of the asset from the raw meteorology.

The model may include:

- observed PR behavior
- AC saturation / clipping behavior
- temperature dependence where data exist
- seasonal or monthly adjustments
- expected losses and operational availability assumptions

#### Step 5: Long-Term Hourly Synthesis

Once the irradiance reference has been corrected and the plant response has been characterized, REPAT generates a synthetic hourly time series.

Each hourly row may contain:

- timestamp
- long-term corrected irradiance
- expected gross generation
- expected net generation
- PR assumption
- clipping flag
- data quality flag
- confidence or scenario label

#### Step 6: Validation

The synthetic output is checked against measured history over the overlapping period. Validation may include:

- monthly energy comparison
- seasonal bias comparison
- error metrics
- PR consistency checks
- reasonableness of clipping behavior

---

## 4. Long-Term Hourly Modelling for Wind Sites

### 4.1 Objective

The objective is to create an hourly long-term wind generation series that can support:

- BESS retrofit studies
- curtailment recovery analysis
- long-term AEP benchmarking
- operational diagnostics
- repowering and life-extension studies

### 4.2 Core Concept

The wind methodology uses:

- measured site SCADA
- wind resource references from reanalysis data
- turbine/farm operational performance behavior

### 4.3 External Reference Data

The proposed reference sources are:

- ERA5
- MERRA-2

These can be used jointly to improve robustness and reduce dependence on a single source.

### 4.4 Typical Wind Inputs

- Site coordinates
- Turbine model
- Hub height
- Rotor diameter
- Power output
- Wind speed
- Wind direction
- Availability and curtailment indicators if available

### 4.5 Wind Methodology Steps

#### Step 1: Data Standardization

SCADA power and wind data are cleaned and aligned to a common time basis.

#### Step 2: Resource Correlation

Measured site wind speed is correlated against ERA5 and MERRA data, with suitable height normalization where required.

#### Step 3: Operational Filtering

Periods with:

- curtailment
- downtime
- icing
- abnormal behavior

are filtered or flagged before deriving long-term performance relationships.

#### Step 4: Power Conversion

The platform estimates expected generation using a combination of:

- measured site behavior
- a cleaned reference power curve
- operational loss assumptions

#### Step 5: Hourly Synthesis

REPAT outputs a long-term hourly CSV with expected net generation and associated explanatory fields.

---

## 5. Proposed Output for Long-Term Hourly CSV

The proposed structure for a normalized hourly CSV is:

- timestamp
- site_id
- site_name
- asset_type
- reference_source
- corrected_resource_value
- expected_gross_output
- expected_net_output
- expected_pr_or_efficiency
- clipping_flag
- curtailment_flag
- outage_excluded_flag
- confidence_class

This structure allows downstream modelling tools to ingest a standard format across solar, wind, and eventually hybrid and BESS studies.

---

## 6. Phase 2: Standalone BESS Analytics

### 6.1 Objective

REPAT will support standalone BESS systems as a dedicated asset class, in addition to solar and wind.

The initial objective is to analyze measured BESS performance in a similar way to current REPAT plant analysis.

### 6.2 Core BESS Inputs

- Rated power (MW)
- Energy capacity (MWh)
- Duration
- Round-trip efficiency
- PCS or inverter rating
- State of charge
- Charge power
- Discharge power
- Availability status
- Throughput
- Alarm and event logs

### 6.3 Initial BESS KPIs

- Availability
- Charge/discharge energy
- Throughput
- Equivalent full cycles
- Round-trip efficiency
- Capacity utilization
- Charge/discharge window compliance
- Dispatch response quality
- Alarms and event occurrence

### 6.4 Future BESS Extensions

After standalone BESS is integrated, REPAT can extend toward:

- PV + BESS hybrid studies
- Wind + BESS hybrid studies
- Curtailment capture estimation
- Time-shifting and peak shaving scenarios
- Storage retrofit sizing based on long-term synthetic hourly plant output

---

## 7. Recommended Development Sequence

The recommended implementation order is:

1. Solar long-term hourly resource and output synthesis
2. Wind long-term hourly resource and output synthesis
3. Standalone BESS site type and analytics
4. Hybrid retrofit and storage sizing studies

This order ensures that the long-term hourly engine exists before advanced storage studies are attempted.

---

## 8. Data Quality and Limitations

The quality of long-term synthetic outputs depends strongly on:

- representativeness of the measured SCADA period
- quality of the site irradiance or wind sensor
- ability to identify outages and curtailment
- correct site metadata
- suitability of the reference meteorological source

The methodology should therefore always report:

- input coverage
- excluded periods
- key assumptions
- uncertainty notes

REPAT should present normalized outputs as engineering model outputs rather than direct historical truth.

---

## 9. Validation Philosophy

Any long-term synthesis should be accompanied by validation outputs such as:

- measured vs modelled monthly energy
- measured vs reference irradiance scatter
- measured vs reference wind speed scatter
- bias metrics
- uncertainty class

This will improve transparency and reinforce technical credibility.

---

## 10. Proposed Positioning in REPAT

This methodology can later be surfaced in the application as:

- a dedicated Methodology page
- a downloadable technical note
- appendix material in generated reports
- client-facing explanatory content in the Knowledge Base

This is recommended because methodological transparency materially increases user trust and supports commercial credibility.

---

## 11. Summary

REPAT’s next-generation analytical framework should rest on three pillars:

- measured operational data
- robust long-term reference data
- transparent normalization logic

The long-term hourly engine provides the foundation for higher-value studies such as storage retrofits, dispatch optimization, and long-term performance benchmarking. Standalone BESS analytics then extend the platform from renewable generation assessment into flexible asset intelligence.

This methodology is intended as the basis for implementation, validation, and future client-facing documentation within REPAT.
