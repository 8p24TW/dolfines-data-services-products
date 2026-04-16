"""English (source) strings for the REPAT SCADA analysis report."""

STRINGS: dict[str, str] = {
    # ── Cover ────────────────────────────────────────────────────────────────
    "cover.subtitle": "SCADA Performance Analysis Report",
    "cover.metadata.project": "Project",
    "cover.metadata.asset": "Asset",
    "cover.metadata.analysis_period": "Analysis period",
    "cover.metadata.technology": "Technology",
    "cover.metadata.issued": "Issued",

    # ── Table of Contents ────────────────────────────────────────────────────
    "toc.title": "Table of Contents",

    # ── Executive Summary ────────────────────────────────────────────────────
    "exec.title": "Executive Summary",
    "exec.kicker": "Highest-value findings",
    "exec.summary": "Portfolio-level findings on performance, availability, data quality, and corrective priorities.",
    "exec.commentary_title": "Overall assessment",
    "exec.commentary.performance": (
        "Average annual PR is {mean_pr} and the latest annual PR is {last_pr}. "
        "Total realised production across the analysed period is {total_energy_mwh}."
    ),
    "exec.commentary.availability.good": (
        "Site availability averages {avail_pct}. "
        "{outage_count} whole-site outage event(s) were inferred from simultaneous daytime inverter dropouts, "
        "which indicates a grid or site-level disturbance rather than isolated inverter trips."
    ),
    "exec.commentary.data_quality.good": (
        "Power completeness is {power_pct} and irradiance completeness is {irr_pct}. "
        "Both inputs are strong enough for confident interpretation."
    ),
    "exec.commentary.data_quality.poor": (
        "Power completeness is {power_pct} and irradiance completeness is {irr_pct}. "
        "Input quality remains a material constraint on fault attribution and any contractual energy discussion."
    ),
    "exec.commentary.critical_months": (
        "The fleet recorded {critical_months} critical PR month(s) below 65% and "
        "{alert_months} further month(s) between 65% and {pr_target}%."
    ),
    "exec.commentary.recoverable_losses": (
        "Annualised recoverable losses are estimated at \u20ac{total_eur}/yr "
        "(downtime: \u20ac{avail_eur}/yr  +  technical underperformance: \u20ac{tech_eur}/yr), "
        "based on {tariff} \u20ac/MWh and averaged over {n_years} year(s). "
        "Addressing the HIGH-priority action items is expected to recover the majority of this gap."
    ),
    "exec.kpi.avg_pr.label": "Average PR",
    "exec.kpi.avg_pr.target": "Target >= {target}%",
    "exec.kpi.fleet_av.label": "Fleet availability",
    "exec.kpi.fleet_av.target": "Target >= 95%",
    "exec.kpi.energy.label": "Actual energy",
    "exec.kpi.actions.label": "Priority actions",
    "exec.kpi.actions.value": "{high_count} high / {medium_count} medium",
    "exec.kpi.losses.label": "Recoverable losses (ann.)",
    "exec.kpi.losses.target": "Downtime \u20ac{avail_eur}  +  Tech. \u20ac{tech_eur}",
    "exec.table.top_actions.title": "Top Recommended Actions",
    "exec.table.top_actions.col.priority": "Priority",
    "exec.table.top_actions.col.category": "Category",
    "exec.table.top_actions.col.loss_mwh": "Estimated loss (MWh)",
    "exec.table.top_actions.col.loss_eur": "Estimated loss (\u20ac)",
    "exec.table.top_actions.col.action": "Action",
    "exec.finding.underperformance.title": "Underperformance",
    "exec.finding.underperformance.body.below": (
        "The site remains below the PR target of {pr_target}%, "
        "so the performance gap remains operationally material."
    ),
    "exec.finding.underperformance.body.on_target": (
        "The site is operating at or above the PR target of {pr_target}% across the analysed period."
    ),
    "exec.finding.data_confidence.title": "Data confidence",
    "exec.finding.data_confidence.body.coherent": (
        "Measured irradiance remains coherent against satellite reference."
    ),
    "exec.finding.data_confidence.body.review": (
        "Irradiance quality or completeness still requires engineering caution."
    ),

    # ── Site Overview ────────────────────────────────────────────────────────
    "site_overview.title": "Site Overview And Technical Scope",
    "site_overview.kicker": "Project baseline",
    "site_overview.summary": "Project context, calculation basis, and fixed site metadata.",
    "site_overview.commentary_title": "Method and asset summary",
    "site_overview.commentary.asset": (
        "{site_name} is a utility-scale solar photovoltaic site with {dc_kwp} kWp DC and "
        "{ac_kw} kW AC, using {n_inverters} {inv_model} inverters and {n_modules} {module_brand} modules."
    ),
    "site_overview.commentary.method": (
        "The report covers {month_count} analysed months of {interval_min}-minute SCADA data. "
        "Performance Ratio remains on the IEC 61724 DC-nameplate basis, "
        "and SARAH satellite irradiance remains the reference for budget comparison."
    ),
    "site_overview.kpi.dc_ac.label": "DC/AC ratio",
    "site_overview.kpi.interval.label": "Sampling interval",
    "site_overview.kpi.interval.value": "{interval_min} min",
    "site_overview.kpi.modules.label": "Modules",
    "site_overview.kpi.inverters.label": "Inverters",
    "site_overview.figure.map.title": "Site Location",
    "site_overview.figure.map.caption": (
        "GPS coordinates: 44\u00b041\u203208.3\u2033N, 0\u00b033\u203234.0\u2033W \u2014 REPAT Solar PV Farm, SW France."
    ),
    "site_overview.table.annual.title": "Annual Performance Summary",
    "site_overview.table.annual.col.year": "Year",
    "site_overview.table.annual.col.pr": "PR",
    "site_overview.table.annual.col.energy": "Energy",
    "site_overview.table.annual.col.irradiation": "Irradiation",
    "site_overview.table.annual.caption": (
        "Yearly performance values provide the annual production and irradiance context for the assessment period."
    ),
    "site_overview.finding.benchmark.title": "Design benchmark",
    "site_overview.finding.benchmark.body": (
        "The contractual design PR at commissioning (COD June 2022) was 80%. "
        "The 79% operating target applied throughout this report reflects approximately 2 years of "
        "module degradation (~0.5%/yr for CdTe) from that baseline."
    ),

    # ── Technical Parameters ─────────────────────────────────────────────────
    "tech_params.title": "Technical Configuration & Analysis Parameters",
    "tech_params.kicker": "Technical basis",
    "tech_params.summary": "Full plant configuration and calculation assumptions used throughout the assessment.",
    "tech_params.commentary_title": "Configuration summary",
    "tech_params.commentary": (
        "{site_name} uses {n_inverters} {inv_model} inverters and {n_modules} {module_brand} modules; "
        "the table below consolidates the fixed inputs and thresholds used throughout the analysis."
    ),
    "tech_params.table.title": "Technical Configuration & Analysis Parameters",
    "tech_params.table.col.parameter": "Parameter",
    "tech_params.table.col.value": "Value",
    "tech_params.table.caption": (
        "Plant configuration, modelling assumptions, and screening thresholds used throughout the report."
    ),
    "tech_params.row.site_name": "Site Name",
    "tech_params.row.cod": "COD (Commercial Operation Date)",
    "tech_params.row.analysis_period": "Analysis Period",
    "tech_params.row.dc_capacity": "DC Capacity",
    "tech_params.row.ac_capacity": "AC Capacity",
    "tech_params.row.dc_ac_ratio": "DC / AC Ratio",
    "tech_params.row.n_modules": "Number of Modules",
    "tech_params.row.module_power": "Module Power",
    "tech_params.row.module_brand": "Module Brand",
    "tech_params.row.module_temp_coeff": "Module Temp. Coefficient",
    "tech_params.row.n_inverters": "Number of Inverters",
    "tech_params.row.inv_model": "Inverter Model",
    "tech_params.row.inv_ac_power": "Inverter AC Power",
    "tech_params.row.inv_ac_power.each": "{value} kW each",
    "tech_params.row.strings_per_inv": "Strings per Inverter",
    "tech_params.row.structure_types": "Structure Types",
    "tech_params.row.n_ptr": "Transformer Substations",
    "tech_params.row.scada_interval": "SCADA Data Interval",
    "tech_params.row.scada_interval.value": "{interval_min} minutes",
    "tech_params.row.pr_method": "PR Calculation Method",
    "tech_params.row.pr_method.value": "IEC 61724 - AC energy / (G_meas/G_STC x P_DC_kWp)",
    "tech_params.row.budget_pr": "Budget PR Assumption",
    "tech_params.row.irr_threshold": "Irradiance Threshold",
    "tech_params.row.irr_threshold.value": "{irr_threshold:.0f} W/m\u00b2 (daytime cut-off)",
    "tech_params.row.ref_irradiance": "Reference Irradiance",
    "tech_params.row.ref_irradiance.value": "SARAH-3 satellite POA data (Nord & Sud orientations)",

    # ── Performance KPI Dashboard ────────────────────────────────────────────
    "perf_kpi.title": "Performance KPI Dashboard",
    "perf_kpi.kicker": "KPI screen",
    "perf_kpi.summary": "High-level screen of performance, availability, data quality, and corrective-action exposure.",
    "perf_kpi.commentary_title": "Dashboard interpretation",
    "perf_kpi.commentary": (
        "This dashboard provides a consolidated technical read-out of performance, availability, "
        "data quality, and corrective priority exposure."
    ),
    "perf_kpi.table.title": "Performance KPI Dashboard",
    "perf_kpi.table.col.metric": "Metric",
    "perf_kpi.table.col.value": "Value",
    "perf_kpi.table.col.target": "Target",
    "perf_kpi.table.col.status": "Status",
    "perf_kpi.row.pr_year": "Site PR ({year})",
    "perf_kpi.row.pr_avg": "PR Average (all years)",
    "perf_kpi.row.energy": "Total Energy Produced",
    "perf_kpi.row.specific_yield": "Specific Yield (annual avg.)",
    "perf_kpi.row.availability": "Mean Inverter Availability",
    "perf_kpi.row.power_completeness": "Power Data Completeness",
    "perf_kpi.row.irr_completeness": "Irradiance Data Completeness",
    "perf_kpi.row.irr_quality": "Irradiance Sensor Quality",
    "perf_kpi.row.high_actions": "High Priority Action Items",
    "perf_kpi.row.clean_pr": "Potential PR (no downtime)",
    "perf_kpi.row.clean_pr.target": "Indicative vs {design_pr}% design",
    "perf_kpi.target.pr": ">= {target}%",
    "perf_kpi.target.gte95": ">= 95%",
    "perf_kpi.target.zero": "0",
    "perf_kpi.target.dash": "-",
    "perf_kpi.target.coherent": "Coherent",
    "perf_kpi.status.on_target": "On target",
    "perf_kpi.status.watch": "Watch",
    "perf_kpi.status.below_target": "Below target",
    "perf_kpi.status.reference": "Reference",
    "perf_kpi.status.coherent": "Coherent",
    "perf_kpi.status.review_required": "Review required",
    "perf_kpi.status.none": "None",
    "perf_kpi.status.open": "Open",
    "perf_kpi.status.indicative": "Indicative scenario",

    # ── Data Quality ─────────────────────────────────────────────────────────
    "data_qual.title": "Data Quality And Irradiance Confidence",
    "data_qual.kicker": "Input quality",
    "data_qual.summary": "Telemetry completeness and irradiance confidence review.",
    "data_qual.commentary_title": "Engineering interpretation",
    "data_qual.commentary.power_irr.good": (
        "Power completeness is {power_pct} and irradiance completeness is {irr_pct}. "
        "Both are at or above the 95% target, so the main energy and PR indicators are suitable for engineering interpretation."
    ),
    "data_qual.commentary.power_irr.poor": (
        "Power completeness is {power_pct} and irradiance completeness is {irr_pct}. "
        "One or both channels remain below the 95% target, so KPI values during missing-data periods "
        "carry elevated uncertainty and should not be used for contractual conclusions without gap recovery."
    ),
    "data_qual.commentary.below95": (
        "{n_below95} inverter(s) fall below 95% telemetry completeness and {n_below90} fall below 90%; "
        "the weakest channel is {worst_inv} at {worst_value}. "
        "Persistent single-inverter gaps bias availability and reliability metrics disproportionately on those units."
    ),
    "data_qual.commentary.sarah_good": (
        "Against SARAH_{name}, measured irradiance correlation is {correlation} with "
        "{suspect_pct} suspect readings; no material irradiance bias is visible."
    ),
    "data_qual.commentary.sarah_poor": (
        "Against SARAH_{name}, measured irradiance correlation is {correlation} with "
        "{suspect_pct} suspect readings; sensor bias remains plausible and should be checked in the field."
    ),
    "data_qual.commentary.no_sarah": (
        "No SARAH comparison is available, so the report relies only on measured irradiance completeness and consistency checks."
    ),
    "data_qual.commentary.stuck": (
        "The analysis detected and removed frozen/stuck SCADA readings on all {n_inverters} inverters \u2014 "
        "a known failure mode on Modbus-based systems where the logger returns the last valid register value "
        "rather than a data gap. "
        "When multiple inverters across different PTRs share identical missing-data windows, the root cause is "
        "upstream (SCADA logger, communication link, or network switch), not individual inverter hardware. "
        "Irradiance sensors should be cross-validated monthly against PVGIS-SARAH3 satellite data; "
        "thermopile pyranometers drift +1\u20133%/yr without heating in humid climates and can suppress "
        "reported PR by a similar margin (IEC 61724-1 Class A: annual calibration, weekly cleaning)."
    ),
    "data_qual.kpi.power_completeness.label": "Power completeness",
    "data_qual.kpi.power_completeness.target": "Target >= 95%",
    "data_qual.kpi.irr_completeness.label": "Irradiance completeness",
    "data_qual.kpi.irr_completeness.target": "Target >= 95%",
    "data_qual.figure.telemetry.title": "Telemetry Completeness Overview",
    "data_qual.figure.telemetry.caption": (
        "Per-inverter completeness is compared with site-wide power and irradiance coverage "
        "to highlight the most material telemetry risks."
    ),

    # ── Data Quality Detail ──────────────────────────────────────────────────
    "data_qual_detail.title": "Data Quality Detail",
    "data_qual_detail.kicker": "Gap pattern review",
    "data_qual_detail.summary": "Monthly missing-data pattern review.",
    "data_qual_detail.commentary_title": "Detailed interpretation",
    "data_qual_detail.finding.sitewide.title": "Site-wide outage pattern",
    "data_qual_detail.finding.sitewide.body": (
        "{n_sitewide} month-level periods show broad site-wide degradation in completeness, "
        "which remains more consistent with logger, network, or export interruptions than isolated inverter faults."
    ),
    "data_qual_detail.finding.weakest.title": "Weakest completeness window",
    "data_qual_detail.finding.weakest.body": (
        "The weakest month-level completeness window occurs in {weakest_month}, "
        "where several inverters degrade simultaneously and the period should be reconciled against "
        "SCADA buffer recovery and logger event history."
    ),
    "data_qual_detail.figure.heatmap.title": "Monthly Inverter Completeness Heatmap",
    "data_qual_detail.figure.heatmap.caption": (
        "Vertical low-completeness bands indicate site-wide outages; "
        "horizontal bands indicate inverter-specific communication gaps."
    ),

    # ── Irradiance Coherence ─────────────────────────────────────────────────
    "irr_coherence.title": "Irradiance Data Coherence Analysis",
    "irr_coherence.kicker": "Sensor confidence",
    "irr_coherence.summary": (
        "Measured irradiance cross-checked against SARAH to screen bias, "
        "suspect readings, and PR denominator reliability."
    ),
    "irr_coherence.commentary_title": "Engineering interpretation",
    "irr_coherence.figure.monthly.title": "Measured Irradiance Vs SARAH Monthly Totals",
    "irr_coherence.figure.monthly.caption": (
        "Measured monthly irradiation is compared against each SARAH reference, "
        "with monthly bias shown on the secondary axis."
    ),
    "irr_coherence.figure.scatter.title": "Measured Irradiance Vs SARAH Scatter",
    "irr_coherence.figure.scatter.caption": (
        "The scatter highlights overall correlation and the extent of random or systematic sensor deviation."
    ),
    "irr_coherence.table.title": "Irradiance Coherence Summary",
    "irr_coherence.table.col.reference": "Reference",
    "irr_coherence.table.col.correlation": "R (corr.)",
    "irr_coherence.table.col.ratio": "Ratio \u00b1 \u03c3",
    "irr_coherence.table.col.suspect_pct": "Suspect %",
    "irr_coherence.table.col.gap_days": "Gap days",
    "irr_coherence.table.col.status": "Status",
    "irr_coherence.status.ok": "OK",
    "irr_coherence.status.review": "Review",

    # ── Performance Overview ─────────────────────────────────────────────────
    "perf_overview.title": "Performance Overview",
    "perf_overview.kicker": "Energy and PR",
    "perf_overview.summary": (
        "Monthly and annual PR trends benchmark energy delivery against the weather-adjusted site reference."
    ),
    "perf_overview.commentary_title": "Performance interpretation",
    "perf_overview.commentary.yoy.decline": (
        "Year-on-year PR moved from {pr_first}% to {pr_last}%, "
        "while annual irradiation shifted by {irr_drop} kWh/m\u00b2. "
        "The PR decline is larger than the irradiation shift alone would justify, "
        "which confirms an operational loss mechanism."
    ),
    "perf_overview.commentary.yoy.aligned": (
        "Year-on-year PR moved from {pr_first}% to {pr_last}%, "
        "while annual irradiation shifted by {irr_drop} kWh/m\u00b2. "
        "The PR movement is broadly aligned with the irradiation change, "
        "so weather remains a major driver of variance."
    ),
    "perf_overview.commentary.specific_yield": (
        "Average specific yield is {spec_yield}. "
        "The period contains {critical_months} month(s) below the 65% critical threshold "
        "and {warning_months} month(s) between 65% and {pr_target}%."
    ),
    "perf_overview.commentary.summer": (
        "If summer PR remains weak while irradiation peaks, soiling, latent downtime, or inverter quality losses "
        "are the likely causes \u2014 a dry-season PR decline with full recovery after autumn rain is the soiling "
        "signature (2\u20138% typical for SW France). "
        "CdTe's \u22120.28%/\u00b0C temperature coefficient means summer PR should nominally exceed c-Si "
        "benchmarks; if it does not, soiling or degradation is eroding that thermal advantage."
    ),
    "perf_overview.kpi.design_pr.label": "Design PR",
    "perf_overview.kpi.avg_pr.label": "Average annual PR",
    "perf_overview.kpi.avg_pr.target": "Target >= 78%",
    "perf_overview.figure.monthly_pr.title": "Monthly Energy, Irradiation And PR",
    "perf_overview.figure.monthly_pr.caption": (
        "Energy bars (left), irradiation line (right, green dashes) and PR line (right, orange) are overlaid "
        "to separate weather-driven output variation from operational underperformance."
    ),
    "perf_overview.figure.daily_yield.title": "Daily Specific Yield And 30-day Rolling Mean",
    "perf_overview.figure.daily_yield.caption": (
        "The daily-yield view highlights sustained low-output windows that monthly averages alone can hide."
    ),
    "perf_overview.table.annual.title": "Annual Performance Detail",
    "perf_overview.table.annual.col.year": "Year",
    "perf_overview.table.annual.col.pr": "PR",
    "perf_overview.table.annual.col.actual_energy": "Actual energy",
    "perf_overview.table.annual.col.reference_energy": "Reference energy",
    "perf_overview.table.annual.col.gap": "Gap to 78%",

    # ── Inverter Performance ─────────────────────────────────────────────────
    "inv_perf.title": "Fleet Inverter Comparison",
    "inv_perf.kicker": "Inverter-level spread",
    "inv_perf.summary": "Inverter fleet comparison between performance and availability.",
    "inv_perf.commentary_title": "Interpretation",
    "inv_perf.commentary": (
        "Fleet mean inverter PR is {fleet_mean} with a standard deviation of {fleet_std}. "
        "{low_both_count} inverter(s) sit in the low-PR / low-availability quadrant, "
        "where uptime recovery is the first lever. "
        "{low_pr_good_av_count} inverter(s) have low PR despite acceptable availability, "
        "pointing toward soiling, string issues, or MPPT behaviour. "
        "Inverters in this second group are priority candidates for an iSolarCloud remote I-V curve scan "
        "before any field dispatch \u2014 the most common causes are unequal MPPT string loading, "
        "soiling heterogeneity, or partial shading. "
        "A persistent spread exceeding 5 pp between best and worst inverters with no correlated availability "
        "gap is the classic DC-side quality-loss signature."
    ),
    "inv_perf.kpi.fleet_mean_pr.label": "Fleet mean PR",
    "inv_perf.kpi.low_both.label": "Low PR + low availability",
    "inv_perf.kpi.low_pr_good_av.label": "Low PR + good availability",
    "inv_perf.figure.scatter.title": "PR Versus Availability",
    "inv_perf.figure.scatter.caption": (
        "The scatter separates downtime-driven losses from running underperformance across the fleet."
    ),
    "inv_perf.table.worst.title": "Lowest PR Inverters",
    "inv_perf.table.worst.col.inverter": "Inverter",
    "inv_perf.table.worst.col.pr": "PR",
    "inv_perf.table.worst.col.availability": "Availability",

    # ── Specific Yield ───────────────────────────────────────────────────────
    "spec_yield.title": "Per-Inverter Specific Yield",
    "spec_yield.kicker": "Quality-loss screening",
    "spec_yield.summary": (
        "Monthly heatmaps highlighting persistent inverter underperformance and peer-relative quality loss."
    ),
    "spec_yield.commentary_title": "Interpretation",
    "spec_yield.commentary": (
        "Fleet mean PR is {fleet_mean}; lowest inverters: {low_pr_names}. "
        "Persistent red months = running but underperforming, not offline. "
        "{worst_dev_str}"
        "Post-rain yield spikes confirm soiling; a stable year-round deficit unresponsive to rainfall "
        "points to a permanent electrical loss (MPPT imbalance, bypassed strings, or junction-box fault)."
    ),
    "spec_yield.figure.heatmap.title": "Specific Yield And PR Heatmaps",
    "spec_yield.figure.heatmap.caption": (
        "The top view separates peer-relative yield quality; "
        "the bottom view keeps downtime inside PR so both mechanisms remain visible."
    ),

    # ── Availability & Reliability ───────────────────────────────────────────
    "avail_rel.title": "Availability And Reliability",
    "avail_rel.kicker": "Uptime and fault recurrence",
    "avail_rel.summary": "Fleet uptime, grid-event exposure, and reliability screening.",
    "avail_rel.commentary_title": "Interpretation",
    "avail_rel.commentary": (
        "Fleet mean availability is {avail_mean}, with {below_95_count} inverter(s) below the 95% threshold "
        "and {whole_site_events} whole-site simultaneous outage event(s) detected. "
        "Mean time to failure across inverters with recorded faults is {fleet_mttf}. "
        "For inverters with MTTF below 5 days, AC relay wear (Fault 038) is the primary suspect \u2014 "
        "trip counts above 500/yr cause contact pitting that prevents reconnection, readable directly "
        "from iSolarCloud Event Log before any field visit. "
        "Whole-site simultaneous drops are grid-event signatures (overvoltage or curtailment) addressed "
        "at MV transformer or DSO level, not at the inverter. "
        "Summer-only availability dips confined to midday hours are typically resolved by cleaning air "
        "inlet filters and verifying fan operation (Fault 036/037)."
    ),
    "avail_rel.kpi.fleet_availability.label": "Fleet availability",
    "avail_rel.kpi.fleet_availability.target": "Target >= 95%",
    "avail_rel.kpi.fleet_mttf.label": "Fleet mean MTTF",
    "avail_rel.kpi.fleet_mttf.target": "Target >= 90 days",
    "avail_rel.figure.trend.title": "Monthly Site Availability",
    "avail_rel.figure.trend.caption": (
        "Monthly availability shows whether the loss exposure is persistent or "
        "concentrated into a small number of events."
    ),
    "avail_rel.table.units.title": "Lowest Availability / Highest Failure Units",
    "avail_rel.table.units.col.metric": "Metric",
    "avail_rel.table.units.col.value": "Value",
    "avail_rel.table.units.row.worst_av": "Worst availability units",
    "avail_rel.table.units.row.top_failures": "Top failure counts",

    # ── Losses ───────────────────────────────────────────────────────────────
    "losses.title": "Losses And Recoverability",
    "losses.kicker": "Budget-to-actual bridge",
    "losses.summary": "Budget-to-actual energy bridge and recoverable loss summary.",
    "losses.commentary_title": "Interpretation",
    "losses.commentary.budget": (
        "The weather-corrected budget is {weather_corrected} against actual production of {actual}."
    ),
    "losses.commentary.breakdown": (
        "Availability loss is {avail_loss}, technical loss is {tech_loss}, "
        "and the residual term indicates {residual_direction} of {residual}."
    ),
    "losses.residual.underperformance": "underperformance",
    "losses.residual.overperformance": "overperformance",
    "losses.commentary.recovery": (
        "Availability loss remains the most recoverable component: a disciplined maintenance-response "
        "improvement could recover approximately {recovery_mwh} over an equivalent period, "
        "while the residual technical loss still requires targeted field checks for soiling, string faults, "
        "MPPT detuning, or DC-side resistance."
    ),
    "losses.commentary.grid": (
        "For context on the French grid environment: RTE/Enedis curtailment events are a growing source of "
        "unattributed loss \u2014 approximately 3 TWh was curtailed nationally in 2025 (up sharply from 2024). "
        "Curtailment periods that are not correctly logged in SCADA appear as unexplained availability or "
        "technical loss. Any month with an unexplained PR dip during peak export hours should be "
        "cross-referenced against grid operator curtailment records before attributing the loss to an inverter fault."
    ),
    "losses.kpi.weather_corrected.label": "Weather-corrected budget",
    "losses.kpi.avail_loss.label": "Availability loss",
    "losses.kpi.tech_loss.label": "Technical loss",
    "losses.figure.waterfall.title": "Energy Loss Waterfall",
    "losses.figure.waterfall.caption": (
        "The waterfall converts the principal loss drivers into energy impact and recovery priority."
    ),
    "losses.figure.monthly_avail.title": "Monthly Availability Loss Breakdown",
    "losses.figure.monthly_avail.caption": (
        "This view shows which months drove the availability deficit across the analysed period."
    ),
    "losses.table.top_opps.title": "Highest Energy-Recovery Opportunities",
    "losses.table.top_opps.col.priority": "Priority",
    "losses.table.top_opps.col.category": "Category",
    "losses.table.top_opps.col.loss_mwh": "Estimated loss (MWh)",
    "losses.table.top_opps.col.loss_eur": "Estimated loss (\u20ac)",
    "losses.table.top_opps.col.action": "Action",

    # ── Targeted Diagnostics ─────────────────────────────────────────────────
    "diag.title": "Targeted Diagnostics",
    "diag.kicker": "Threshold behaviour",
    "diag.summary": "Start and stop behaviour screening for threshold or wake-up anomalies.",
    "diag.commentary_title": "Interpretation",
    "diag.commentary.max_dev": (
        "Maximum fleet-relative startup deviation is {max_start} and maximum stop deviation is {max_stop}. "
        "Persistent late start / early stop signatures remain an efficient screen "
        "for non-harmonised inverter thresholds."
    ),
    "diag.commentary.large_dev": (
        "Deviations beyond roughly 15 minutes are unlikely to be explained by noise alone and remain "
        "consistent with high startup voltage thresholds, wake-up sensitivity, or recurrent local trips."
    ),
    "diag.commentary.contained_dev": (
        "Start/stop deviations are present but relatively contained, so they remain a secondary issue "
        "compared with the dominant availability and PR losses."
    ),
    "diag.commentary.red_outliers": (
        "Red-coded outliers above 15 minutes are {flagged_red}; "
        "these units warrant configuration review before further hardware intervention."
    ),
    "diag.commentary.amber_zone": (
        "Amber-zone deviations between 8 and 15 minutes remain visible on {flagged_amber}; "
        "these units should be monitored for seasonal persistence."
    ),
    "diag.commentary.late_start": (
        "Late-start signatures worse in winter than summer indicate the MPPT startup threshold is "
        "set too high (Fault 601) \u2014 adjustable via iSolarCloud to 0.5% of rated power. "
        "Early-stop deviations at dusk typically reflect string voltage dropping below the 200V MPPT minimum, "
        "most often from partial shading."
    ),
    "diag.figure.start_stop.title": "Start And Stop Deviation",
    "diag.figure.start_stop.caption": (
        "Start and stop deviations highlight threshold non-uniformity, "
        "wake-up sensitivity, and recurrent switching anomalies."
    ),

    # ── Conclusions ──────────────────────────────────────────────────────────
    "conclusions.title": "Conclusions And Recommendations",
    "conclusions.kicker": "Synthesis",
    "conclusions.summary": "Consolidated technical conclusions and recommended next actions.",
    "conclusions.commentary_title": "Conclusion",
    "conclusions.commentary.main": (
        "The site closes the period at {mean_pr} average PR and {fleet_av} average availability. "
        "The dominant loss mechanisms remain operational rather than purely meteorological."
    ),
    "conclusions.commentary.recovery": (
        "Whole-site events, low-performing inverters, and the waterfall all point toward recoverable energy "
        "rather than an irreducible weather effect. "
        "Availability loss remains {avail_loss} and technical loss remains {tech_loss}."
    ),
    "conclusions.commentary.data_quality": (
        "Data quality remains adequate for engineering triage but not perfect: "
        "power completeness is {power_pct} and irradiance completeness is {irr_pct}."
    ),
    "conclusions.finding.recommended_action": "Recommended action: {action}",
    "conclusions.kpi.avg_pr.label": "Average PR",
    "conclusions.kpi.avg_pr.target": "Target >= 78%",
    "conclusions.kpi.fleet_av.label": "Fleet availability",
    "conclusions.kpi.fleet_av.target": "Target >= 95%",
    "conclusions.kpi.high_actions.label": "High-priority actions",
    "conclusions.finding.no_critical.title": "No critical actions",
    "conclusions.finding.no_critical.body": (
        "No high-priority corrective action was generated by the current thresholds."
    ),

    # ── Action Punchlist ─────────────────────────────────────────────────────
    "punchlist.title": "Action Punchlist",
    "punchlist.kicker": "Corrective-action register",
    "punchlist.summary": "Full action register for maintenance planning and client follow-up.",
    "punchlist.commentary_title": "Action register summary",
    "punchlist.commentary": (
        "The punchlist contains {n_actions} actions ranked by priority and estimated energy impact. "
        "High-priority items should be treated as the first corrective phase; "
        "medium-priority items remain relevant once the dominant downtime and PR losses are stabilised."
    ),
    "punchlist.table.title": "Full Action Punchlist",
    "punchlist.table.col.priority": "Priority",
    "punchlist.table.col.category": "Category",
    "punchlist.table.col.loss_mwh": "Estimated loss (MWh)",
    "punchlist.table.col.loss_eur": "Estimated loss (\u20ac)",
    "punchlist.table.col.issue": "Issue",
    "punchlist.table.col.action": "Recommended action",

    # ── Technology Risk Register ─────────────────────────────────────────────
    "tech_risk.title": "Technology Risk Register",
    "tech_risk.kicker": "Sungrow SG250HX & First Solar CdTe",
    "tech_risk.summary": (
        "Key failure modes, performance risks, and diagnostic actions specific to "
        "the inverter and module technologies deployed at this site."
    ),
    "tech_risk.commentary_title": "Risk context",
    "tech_risk.commentary.register": (
        "This register consolidates {high_count} HIGH-priority and {med_count} MEDIUM-priority "
        "technology-specific risks derived from field experience across comparable French utility-scale PV sites, "
        "Sungrow EMEA fault documentation, First Solar technical papers, and NREL/IEA monitoring standards."
    ),
    "tech_risk.commentary.context": (
        "HIGH items represent failure modes with confirmed field precedent and material energy loss potential "
        "that can persist undetected without targeted inspection. "
        "MEDIUM items are relevant operational watch-points. "
        "INFO items provide benchmarking context to avoid misinterpreting normal technology behaviour as faults."
    ),
    "tech_risk.table.title": "Technology Risk Register \u2014 Sungrow SG250HX & First Solar Series 6",
    "tech_risk.table.col.priority": "Priority",
    "tech_risk.table.col.equipment": "Equipment",
    "tech_risk.table.col.risk": "Risk / What to Watch",
    "tech_risk.table.col.action": "Diagnostic / Action",
    "tech_risk.priority.high": "HIGH",
    "tech_risk.priority.medium": "MEDIUM",
    "tech_risk.priority.info": "INFO",
    # Risk rows — Risk column
    "tech_risk.row.ac_relay.risk": (
        "AC Relay Wear (Fault 038) \u2014 high trip-count sites develop pitted contacts; "
        "inverter fails to reconnect after trip."
    ),
    "tech_risk.row.dc_insulation.risk": (
        "DC Insulation Fault (Fault 039) \u2014 triggered after rain if string Riso < 50 k\u03a9. "
        "High risk with third-party MC4 connectors or cables pinched under tracker rails."
    ),
    "tech_risk.row.mppt_wiring.risk": (
        "MPPT Wiring Error \u2014 persistent single-inverter PR 10\u201315% below fleet with no fault alarms "
        "and no seasonal variation. Can persist for years undetected."
    ),
    "tech_risk.row.pid.risk": (
        "PID / TCO Corrosion \u2014 power loss at negative-string-end modules from sodium migration "
        "and TCO corrosion. Risk elevated in ungrounded high-voltage systems."
    ),
    "tech_risk.row.pr_decline.risk": (
        "PR Decline Exceeding Warranted Rate \u2014 warranted 0.55%/yr (Cu back contact) or 0.2%/yr (CuRe). "
        "Fleet-wide PR decline >1%/yr requires priority investigation."
    ),
    "tech_risk.row.thermal.risk": (
        "Thermal Overtemperature (Faults 036/037) \u2014 summer midday trips if ambient >45\u00b0C near cabinet, "
        "seized fan bearings, or blocked air inlet filters."
    ),
    "tech_risk.row.curtailment.risk": (
        "French Grid Curtailment Not Logged (SUN-014) \u2014 RTE/Enedis curtailment appearing as unexplained "
        "PR dips. ~3 TWh curtailed in France in 2025, rising sharply."
    ),
    "tech_risk.row.irr_drift.risk": (
        "Irradiance Sensor Drift \u2014 thermopile pyranometers drift +1\u20133%/yr without heating in humid "
        "climates, making PR appear to decline. Reference cells overestimate daily irradiation by >2%."
    ),
    "tech_risk.row.hot_spot.risk": (
        "Hot Spot Detection Difficulty \u2014 monolithic CdTe structure and glass-glass encapsulation produce "
        "smaller surface temperature gradients than c-Si; standard IR surveys miss them."
    ),
    "tech_risk.row.cdte_temp.risk": (
        "CdTe Temperature Coefficient Advantage \u2014 Pmax coeff. \u22120.28%/\u00b0C vs c-Si \u22120.35 "
        "to \u22120.50%/\u00b0C. Summer PR should exceed c-Si benchmarks \u2014 this is expected, not a fault."
    ),
    "tech_risk.row.iv_curve.risk": (
        "iSolarCloud Remote I-V Curve Scan \u2014 full-plant diagnostic identifies dust, cracks, diode shorts, "
        "MPPT mismatch, and PID attenuation in ~15 minutes with <0.5% accuracy."
    ),
    "tech_risk.row.clipping.risk": (
        "Clipping Loss Underestimation \u2014 at DC/AC ratio 1.27 (this site), clipping occurs ~3\u20134% of "
        "annual operating hours. 10-min SCADA averages mask true clipping magnitude."
    ),
    # Risk rows — Action column
    "tech_risk.row.ac_relay.action": (
        "Extract trip count from iSolarCloud Event Log. If >500 trips/yr, replace relay proactively. "
        "Check SPDs in LV cabinet for earth short. Listen for relay click on restart \u2014 absent = failed relay."
    ),
    "tech_risk.row.dc_insulation.action": (
        "String-by-string isolation test to locate affected string. Megger at 1000 V DC (target >1 M\u03a9). "
        "Replace third-party MC4 connectors with OEM-compatible type."
    ),
    "tech_risk.row.mppt_wiring.action": (
        "Audit strings per MPPT vs single-line diagram. Calculate DC power per MPPT vs rated input. "
        "Run iSolarCloud I-V curve scan to identify anomalous MPPT channels."
    ),
    "tech_risk.row.pid.action": (
        "EL imaging survey prioritising negative-string-end modules. "
        "IV-curve for Voc and fill factor loss signature. Verify edge seal integrity on suspect modules."
    ),
    "tech_risk.row.pr_decline.action": (
        "EL/IV testing on module sample. Review soiling log and cleaning records. "
        "Check inverter efficiency trending. Compare irradiance sensor vs PVGIS-SARAH3 for sensor drift."
    ),
    "tech_risk.row.thermal.action": (
        "Inspect fans and air filters at every maintenance visit. "
        "500 mm clearance required around enclosure. "
        "Install shade canopy if ambient routinely >45\u00b0C in summer."
    ),
    "tech_risk.row.curtailment.action": (
        "Verify curtailment command timestamps logged in SCADA. "
        "Cross-reference with grid operator records for months with unexplained PR drops. "
        "Exclude curtailed periods from contractual PR."
    ),
    "tech_risk.row.irr_drift.action": (
        "Monthly comparison of on-site irradiation vs PVGIS-SARAH3. "
        "Annual sensor calibration (IEC 61724-1 Class A). Weekly cleaning log. "
        "Replace Class C instruments with ISO 9060 Class A for contractual PR."
    ),
    "tech_risk.row.hot_spot.action": (
        "Use high-sensitivity IR camera (NETD <50 mK). "
        "Perform thermographic survey at >600 W/m\u00b2 irradiance. "
        "Confirm with IV-curve fill factor loss measurement on suspect modules."
    ),
    "tech_risk.row.cdte_temp.action": (
        "Do not apply c-Si PR benchmarks to CdTe plants in hot conditions. "
        "Summer PR declining toward c-Si levels may signal module degradation or soiling eroding "
        "the thermal advantage."
    ),
    "tech_risk.row.iv_curve.action": (
        "Schedule remote I-V curve scan via iSolarCloud before any field dispatch for unexplained "
        "underperformance. Results localise affected strings without site visit."
    ),
    "tech_risk.row.clipping.action": (
        "Configure SCADA at 5-min resolution to capture clipping accurately. "
        "Apply clipping correction factor when comparing SCADA PR to hourly yield model."
    ),

    # ── Appendix — MTTF Overview ─────────────────────────────────────────────
    "app_mttf_overview.title": "Appendix - Reliability Overview",
    "app_mttf_overview.summary": "Fleet-wide MTTF and failure-count diagnostics for maintenance planning.",
    "app_mttf_overview.commentary_title": "Reliability interpretation",
    "app_mttf_overview.commentary.main": (
        "Fleet mean MTTF is {fleet_mttf} against the 90-day reliability benchmark used for maintenance "
        "screening. {high_fault} inverter(s) exceed 100 fault events and {med_fault} more sit in the "
        "30\u2013100 fault range."
    ),
    "app_mttf_overview.commentary.worst": "The highest recurring-fault units are {worst_faults}.",
    "app_mttf_overview.commentary.ranking": (
        "The ranking charts screen recurrence severity, while the following detail table preserves the "
        "all-inverter traceability needed for maintenance planning."
    ),
    "app_mttf_overview.figure.failures.title": "Failure Count Ranking",
    "app_mttf_overview.figure.failures.caption": (
        "Highest fault-event counts identify the units requiring immediate root-cause review."
    ),
    "app_mttf_overview.figure.mttf.title": "Lowest Mean Time To Failure",
    "app_mttf_overview.figure.mttf.caption": (
        "MTTF highlights the units with the fastest recurrence rate, not just the largest lifetime count."
    ),
    "app_mttf_overview.note": (
        "SCADA confirms recurrence patterns but cannot identify exact trip modes without OEM alarm "
        "and fault-code exports."
    ),

    # ── Appendix — MTTF Detail ───────────────────────────────────────────────
    "app_mttf_detail.title": "Appendix - MTTF Detail - All Inverters",
    "app_mttf_detail.summary": "All-inverter reliability detail retained for engineering traceability.",
    "app_mttf_detail.table.title": "MTTF Detail - All Inverters",
    "app_mttf_detail.table.col.inverter": "Inverter",
    "app_mttf_detail.table.col.faults": "Faults",
    "app_mttf_detail.table.col.run_hrs": "Run hrs",
    "app_mttf_detail.table.col.mttf_d": "MTTF (d)",
    "app_mttf_detail.table.col.mttf_h": "MTTF (h)",
    "app_mttf_detail.table.col.status": "Status",
    "app_mttf_detail.table.caption": (
        "Critical = more than 100 fault events over the analysed period; Warning = 31 to 100 events."
    ),
    "app_mttf_detail.status.critical": "Critical",
    "app_mttf_detail.status.warning": "Warning",
    "app_mttf_detail.status.normal": "Normal",

    # ── Appendix — Weather Correlation ───────────────────────────────────────
    "app_weather.title": "Appendix - Weather Correlation",
    "app_weather.summary": (
        "Secondary weather-context diagnostics retained in appendix to preserve readability "
        "of the main narrative."
    ),
    "app_weather.commentary_title": "Weather-context interpretation",
    "app_weather.figure.title": "PR Vs Temperature And Rainfall",
    "app_weather.figure.caption": (
        "Monthly PR is compared against rainfall and temperature, "
        "alongside a daily temperature-coloured PR view."
    ),

    # ── Appendix — Clipping ──────────────────────────────────────────────────
    "app_clipping.title": "Appendix - Clipping Analysis",
    "app_clipping.summary": "Near-clipping diagnostics for inverter loading review.",
    "app_clipping.commentary_title": "Clipping interpretation",
    "app_clipping.commentary": (
        "Near-clipping occurs on {near_pct} of valid daytime intervals at the site level, "
        "which is useful for screening possible AC-ceiling exposure during high-irradiance periods."
    ),
    "app_clipping.figure.title": "Clipping Diagnostics",
    "app_clipping.figure.caption": (
        "Power-distribution, irradiance-bin, and top-inverter views screen "
        "where near-ceiling operation is concentrated."
    ),

    # ── Appendix — Limitations ───────────────────────────────────────────────
    "app_limitations.title": "Appendix - Analytical Scope And Data Limitations",
    "app_limitations.summary": (
        "Summary of the analytical scope completed for this assessment and the principal data "
        "constraints affecting interpretation."
    ),
    "app_limitations.table.scope.title": "Analytical Scope Completed",
    "app_limitations.table.scope.col.activity": "Activity",
    "app_limitations.table.scope.col.status": "Status",
    "app_limitations.table.scope.col.notes": "Notes",
    "app_limitations.table.constraints.title": "Analytical Constraints",
    "app_limitations.table.constraints.col.analysis": "Analysis",
    "app_limitations.table.constraints.col.status": "Status",
    "app_limitations.table.constraints.col.notes": "Notes",
    "app_limitations.table.priority.title": "Priority Action Snapshot",
    "app_limitations.table.priority.col.priority": "Priority",
    "app_limitations.table.priority.col.category": "Category",
    "app_limitations.table.priority.col.estimated_loss": "Estimated loss",
    "app_limitations.table.priority.col.action": "Recommended action",
    # Scope rows
    "app_limitations.scope.data_avail.activity": "Data availability assessment",
    "app_limitations.scope.data_avail.status": "Completed",
    "app_limitations.scope.data_avail.notes": "Per-inverter and site-level telemetry completeness reviewed.",
    "app_limitations.scope.pr.activity": "Performance ratio assessment",
    "app_limitations.scope.pr.status": "Completed",
    "app_limitations.scope.pr.notes": "Monthly and annual PR calculated on the IEC 61724 DC-kWp basis.",
    "app_limitations.scope.irr.activity": "Irradiance coherence (SARAH-3)",
    "app_limitations.scope.irr.status": "Completed",
    "app_limitations.scope.irr.notes": (
        "On-site irradiance cross-checked against SARAH reference, "
        "including bias and suspect-reading screening."
    ),
    "app_limitations.scope.avail.activity": "Availability and reliability review",
    "app_limitations.scope.avail.status": "Completed",
    "app_limitations.scope.avail.notes": (
        "Fleet uptime, inverter-level availability, and fault recurrence screened."
    ),
    "app_limitations.scope.loss.activity": "Loss attribution",
    "app_limitations.scope.loss.status": "Completed",
    "app_limitations.scope.loss.notes": (
        "Budget, weather correction, availability loss, technical loss, and residual reviewed."
    ),
    "app_limitations.scope.yield.activity": "Per-inverter specific yield",
    "app_limitations.scope.yield.status": "Completed",
    "app_limitations.scope.yield.notes": (
        "Monthly inverter heatmaps reviewed for recurring underperformance patterns."
    ),
    "app_limitations.scope.startstop.activity": "Start/stop signature screening",
    "app_limitations.scope.startstop.status": "Completed",
    "app_limitations.scope.startstop.notes": (
        "Fleet-relative wake-up and shut-down timing deviations screened for threshold anomalies."
    ),
    "app_limitations.scope.weather.activity": "Weather-correlation review",
    "app_limitations.scope.weather.status": "Completed",
    "app_limitations.scope.weather.notes": (
        "Rainfall and temperature context considered in the diagnostic workflow."
    ),
    # Constraint rows
    "app_limitations.constraint.acdc.analysis": "Inverter AC/DC efficiency",
    "app_limitations.constraint.acdc.status": "Not possible",
    "app_limitations.constraint.acdc.notes": "No DC current or DC power channels are available in the export.",
    "app_limitations.constraint.string.analysis": "String-level fault detection",
    "app_limitations.constraint.string.status": "Not possible",
    "app_limitations.constraint.string.notes": "The SCADA extract is limited to inverter-level AC production.",
    "app_limitations.constraint.transients.analysis": "Short transients",
    "app_limitations.constraint.transients.status": "Limited",
    "app_limitations.constraint.transients.notes": (
        "The 10-minute sampling interval is too coarse for sub-interval fault isolation."
    ),
    "app_limitations.constraint.downtime.analysis": "Downtime root cause",
    "app_limitations.constraint.downtime.status": "Limited",
    "app_limitations.constraint.downtime.notes": (
        "Alarm and fault-code channels are absent, so trips are classified indirectly."
    ),
    "app_limitations.constraint.curtailment.analysis": "Curtailment certainty",
    "app_limitations.constraint.curtailment.status": "Limited",
    "app_limitations.constraint.curtailment.notes": (
        "Without explicit export-limit flags, curtailment remains heuristic."
    ),
    "app_limitations.constraint.degradation.analysis": "Degradation certainty",
    "app_limitations.constraint.degradation.status": "Limited",
    "app_limitations.constraint.degradation.notes": (
        "The available time horizon remains too short for a statistically robust long-term degradation estimate."
    ),
    "app_limitations.constraint.soiling.analysis": "Soiling quantification",
    "app_limitations.constraint.soiling.status": "Not possible",
    "app_limitations.constraint.soiling.notes": (
        "No dedicated soiling sensor or IV-curve dataset is available to isolate accumulation rates."
    ),
}
