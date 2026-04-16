"""French translations for the PVPAT SCADA analysis report."""

STRINGS: dict[str, str] = {
    # ── Cover ────────────────────────────────────────────────────────────────
    "cover.subtitle": "Rapport d\u2019Analyse SCADA de Performance PV",
    "cover.metadata.project": "Projet",
    "cover.metadata.asset": "Actif",
    "cover.metadata.analysis_period": "P\u00e9riode d\u2019analyse",
    "cover.metadata.technology": "Technologies",
    "cover.metadata.issued": "\u00c9mis le",

    # ── Table of Contents ────────────────────────────────────────────────────
    "toc.title": "Table des mati\u00e8res",

    # ── Executive Summary ────────────────────────────────────────────────────
    "exec.title": "R\u00e9sum\u00e9 Ex\u00e9cutif",
    "exec.kicker": "Constats \u00e0 plus forte valeur ajout\u00e9e",
    "exec.summary": (
        "Principaux constats sur la performance, la disponibilit\u00e9, la qualit\u00e9 des donn\u00e9es "
        "et les priorit\u00e9s correctives."
    ),
    "exec.commentary_title": "\u00c9valuation globale",
    "exec.commentary.performance": (
        "Le PR annuel moyen est {mean_pr} et le dernier PR annuel est {last_pr}. "
        "La production totale r\u00e9alis\u00e9e sur la p\u00e9riode analys\u00e9e est {total_energy_mwh}."
    ),
    "exec.commentary.availability.good": (
        "La disponibilit\u00e9 de site est en moyenne de {avail_pct}. "
        "{outage_count} \u00e9v\u00e9nement(s) de coupure totale du site ont \u00e9t\u00e9 d\u00e9tect\u00e9s "
        "par arr\u00eats simultan\u00e9s des onduleurs en journ\u00e9e, "
        "ce qui indique une perturbation r\u00e9seau ou de niveau site plut\u00f4t que des d\u00e9fauts "
        "d\u2019onduleurs isol\u00e9s."
    ),
    "exec.commentary.data_quality.good": (
        "La compl\u00e9tude de puissance est {power_pct} et la compl\u00e9tude d\u2019irradiance est {irr_pct}. "
        "Les deux sources de donn\u00e9es sont suffisamment fiables pour une interpr\u00e9tation ing\u00e9nierie."
    ),
    "exec.commentary.data_quality.poor": (
        "La compl\u00e9tude de puissance est {power_pct} et la compl\u00e9tude d\u2019irradiance est {irr_pct}. "
        "La qualit\u00e9 des donn\u00e9es constitue une contrainte importante pour l\u2019attribution des d\u00e9fauts "
        "et toute discussion contractuelle sur l\u2019\u00e9nergie."
    ),
    "exec.commentary.critical_months": (
        "La flotte a enregistr\u00e9 {critical_months} mois critique(s) de PR inf\u00e9rieur \u00e0 65\u00a0% "
        "et {alert_months} mois suppl\u00e9mentaire(s) entre 65\u00a0% et {pr_target}\u00a0%."
    ),
    "exec.commentary.recoverable_losses": (
        "Les pertes r\u00e9cup\u00e9rables annualis\u00e9es sont estim\u00e9es \u00e0 {total_eur}\u00a0\u20ac/an "
        "(arr\u00eats\u00a0: {avail_eur}\u00a0\u20ac/an + sous-performance technique\u00a0: {tech_eur}\u00a0\u20ac/an), "
        "sur la base de {tariff}\u00a0\u20ac/MWh en moyenne sur {n_years} ann\u00e9e(s). "
        "Le traitement des actions prioritaires \u00ab\u00a0HAUTE\u00a0\u00bb doit permettre de r\u00e9cup\u00e9rer "
        "la majorit\u00e9 de cet \u00e9cart."
    ),
    "exec.kpi.avg_pr.label": "PR moyen",
    "exec.kpi.avg_pr.target": "Cible \u2265 {target}\u00a0%",
    "exec.kpi.fleet_av.label": "Disponibilit\u00e9 flotte",
    "exec.kpi.fleet_av.target": "Cible \u2265 95\u00a0%",
    "exec.kpi.energy.label": "\u00c9nergie produite",
    "exec.kpi.actions.label": "Actions prioritaires",
    "exec.kpi.actions.value": "{high_count} hautes / {medium_count} moyennes",
    "exec.kpi.losses.label": "Pertes r\u00e9cup\u00e9rables (ann.)",
    "exec.kpi.losses.target": "Arr\u00eats {avail_eur}\u00a0\u20ac  +  Tech. {tech_eur}\u00a0\u20ac",
    "exec.table.top_actions.title": "Principales Actions Recommand\u00e9es",
    "exec.table.top_actions.col.priority": "Priorit\u00e9",
    "exec.table.top_actions.col.category": "Cat\u00e9gorie",
    "exec.table.top_actions.col.loss_mwh": "Perte estim\u00e9e (MWh)",
    "exec.table.top_actions.col.loss_eur": "Perte estim\u00e9e (\u20ac)",
    "exec.table.top_actions.col.action": "Action",
    "exec.finding.underperformance.title": "Sous-performance",
    "exec.finding.underperformance.body.below": (
        "Le site reste en-de\u00e7\u00e0 de la cible de PR \u00e0 {pr_target}\u00a0%, "
        "l\u2019\u00e9cart de performance reste donc op\u00e9rationnellement significatif."
    ),
    "exec.finding.underperformance.body.on_target": (
        "Le site op\u00e8re \u00e0 ou au-dessus de la cible de PR \u00e0 {pr_target}\u00a0% "
        "sur la p\u00e9riode analys\u00e9e."
    ),
    "exec.finding.data_confidence.title": "Confiance dans les donn\u00e9es",
    "exec.finding.data_confidence.body.coherent": (
        "L\u2019irradiance mesur\u00e9e reste coh\u00e9rente par rapport \u00e0 la r\u00e9f\u00e9rence satellite."
    ),
    "exec.finding.data_confidence.body.review": (
        "La qualit\u00e9 ou la compl\u00e9tude de l\u2019irradiance n\u00e9cessite encore une vigilance ing\u00e9nierie."
    ),

    # ── Site Overview ────────────────────────────────────────────────────────
    "site_overview.title": "Pr\u00e9sentation du Site et P\u00e9rim\u00e8tre Technique",
    "site_overview.kicker": "R\u00e9f\u00e9rentiel projet",
    "site_overview.summary": "Contexte projet, base de calcul et m\u00e9tadonn\u00e9es fixes du site.",
    "site_overview.commentary_title": "M\u00e9thode et synth\u00e8se des actifs",
    "site_overview.commentary.asset": (
        "{site_name} est un parc solaire photovolta\u00efque de grande puissance avec {dc_kwp}\u00a0kWc DC "
        "et {ac_kw}\u00a0kW AC, utilisant {n_inverters} onduleurs {inv_model} "
        "et {n_modules} modules {module_brand}."
    ),
    "site_overview.commentary.method": (
        "Le rapport couvre {month_count} mois analys\u00e9s de donn\u00e9es SCADA au pas de {interval_min}\u00a0minutes. "
        "Le Ratio de Performance (PR) est calcul\u00e9 selon la base DC-puissance nominale IEC\u00a061724, "
        "et l\u2019irradiance satellite SARAH reste la r\u00e9f\u00e9rence pour la comparaison budg\u00e9taire."
    ),
    "site_overview.kpi.dc_ac.label": "Ratio DC/AC",
    "site_overview.kpi.interval.label": "Pas d\u2019\u00e9chantillonnage",
    "site_overview.kpi.interval.value": "{interval_min}\u00a0min",
    "site_overview.kpi.modules.label": "Modules",
    "site_overview.kpi.inverters.label": "Onduleurs",
    "site_overview.figure.map.title": "Localisation du Site",
    "site_overview.figure.map.caption": (
        "Coordonn\u00e9es GPS\u00a0: 44\u00b041\u203208,3\u2033N, 0\u00b033\u203234,0\u2033W "
        "\u2014 Parc solaire PVPAT, SO France."
    ),
    "site_overview.table.annual.title": "Synth\u00e8se des Performances Annuelles",
    "site_overview.table.annual.col.year": "Ann\u00e9e",
    "site_overview.table.annual.col.pr": "PR",
    "site_overview.table.annual.col.energy": "\u00c9nergie",
    "site_overview.table.annual.col.irradiation": "Irradiation",
    "site_overview.table.annual.caption": (
        "Les valeurs de performance annuelles fournissent le contexte de production et d\u2019irradiance "
        "pour la p\u00e9riode d\u2019\u00e9valuation."
    ),
    "site_overview.finding.benchmark.title": "R\u00e9f\u00e9rentiel de conception",
    "site_overview.finding.benchmark.body": (
        "Le PR de conception contractuel \u00e0 la mise en service (COD juin 2022) \u00e9tait de 80\u00a0%. "
        "La cible op\u00e9rationnelle de 79\u00a0% appliqu\u00e9e tout au long de ce rapport refl\u00e8te "
        "environ 2 ans de d\u00e9gradation des modules (~0,5\u00a0%/an pour le CdTe) depuis cette base."
    ),

    # ── Technical Parameters ─────────────────────────────────────────────────
    "tech_params.title": "Configuration Technique & Param\u00e8tres d\u2019Analyse",
    "tech_params.kicker": "Base technique",
    "tech_params.summary": (
        "Configuration compl\u00e8te de la centrale et hypoth\u00e8ses de calcul utilis\u00e9es tout au long "
        "de l\u2019\u00e9valuation."
    ),
    "tech_params.commentary_title": "Synth\u00e8se de la configuration",
    "tech_params.commentary": (
        "{site_name} utilise {n_inverters} onduleurs {inv_model} et {n_modules} modules {module_brand}\u00a0; "
        "le tableau ci-dessous consolide les entr\u00e9es fixes et les seuils utilis\u00e9s tout au long "
        "de l\u2019analyse."
    ),
    "tech_params.table.title": "Configuration Technique & Param\u00e8tres d\u2019Analyse",
    "tech_params.table.col.parameter": "Param\u00e8tre",
    "tech_params.table.col.value": "Valeur",
    "tech_params.table.caption": (
        "Configuration de la centrale, hypoth\u00e8ses de mod\u00e9lisation et seuils de filtrage "
        "utilis\u00e9s dans le rapport."
    ),
    "tech_params.row.site_name": "Nom du site",
    "tech_params.row.cod": "COD (Date de mise en service)",
    "tech_params.row.analysis_period": "P\u00e9riode d\u2019analyse",
    "tech_params.row.dc_capacity": "Puissance DC",
    "tech_params.row.ac_capacity": "Puissance AC",
    "tech_params.row.dc_ac_ratio": "Ratio DC / AC",
    "tech_params.row.n_modules": "Nombre de modules",
    "tech_params.row.module_power": "Puissance module",
    "tech_params.row.module_brand": "Marque module",
    "tech_params.row.module_temp_coeff": "Coefficient temp. module",
    "tech_params.row.n_inverters": "Nombre d\u2019onduleurs",
    "tech_params.row.inv_model": "Mod\u00e8le d\u2019onduleur",
    "tech_params.row.inv_ac_power": "Puissance AC onduleur",
    "tech_params.row.inv_ac_power.each": "{value}\u00a0kW par unit\u00e9",
    "tech_params.row.strings_per_inv": "Strings par onduleur",
    "tech_params.row.structure_types": "Types de structure",
    "tech_params.row.n_ptr": "Postes de transformation",
    "tech_params.row.scada_interval": "Intervalle SCADA",
    "tech_params.row.scada_interval.value": "{interval_min}\u00a0minutes",
    "tech_params.row.pr_method": "M\u00e9thode de calcul du PR",
    "tech_params.row.pr_method.value": "IEC\u00a061724 - \u00c9nergie AC / (G_mes/G_STC \u00d7 P_DC_kWc)",
    "tech_params.row.budget_pr": "PR budg\u00e9taire",
    "tech_params.row.irr_threshold": "Seuil d\u2019irradiance",
    "tech_params.row.irr_threshold.value": "{irr_threshold:.0f}\u00a0W/m\u00b2 (seuil diurne)",
    "tech_params.row.ref_irradiance": "Irradiance de r\u00e9f\u00e9rence",
    "tech_params.row.ref_irradiance.value": "Donn\u00e9es satellite SARAH-3 POA (orientations Nord & Sud)",

    # ── Performance KPI Dashboard ────────────────────────────────────────────
    "perf_kpi.title": "Tableau de Bord KPI de Performance",
    "perf_kpi.kicker": "\u00c9cran KPI",
    "perf_kpi.summary": (
        "\u00c9cran synth\u00e9tique de la performance, de la disponibilit\u00e9, "
        "de la qualit\u00e9 des donn\u00e9es et de l\u2019exposition aux actions correctives."
    ),
    "perf_kpi.commentary_title": "Lecture du tableau de bord",
    "perf_kpi.commentary": (
        "Ce tableau de bord fournit une lecture technique consolid\u00e9e de la performance, "
        "de la disponibilit\u00e9, de la qualit\u00e9 des donn\u00e9es et de l\u2019exposition aux actions correctives."
    ),
    "perf_kpi.table.title": "Tableau de Bord KPI de Performance",
    "perf_kpi.table.col.metric": "Indicateur",
    "perf_kpi.table.col.value": "Valeur",
    "perf_kpi.table.col.target": "Cible",
    "perf_kpi.table.col.status": "Statut",
    "perf_kpi.row.pr_year": "PR site ({year})",
    "perf_kpi.row.pr_avg": "PR moyen (toutes ann\u00e9es)",
    "perf_kpi.row.energy": "\u00c9nergie totale produite",
    "perf_kpi.row.specific_yield": "Production sp\u00e9cifique (moy. ann.)",
    "perf_kpi.row.availability": "Disponibilit\u00e9 moyenne onduleurs",
    "perf_kpi.row.power_completeness": "Compl\u00e9tude donn\u00e9es puissance",
    "perf_kpi.row.irr_completeness": "Compl\u00e9tude donn\u00e9es irradiance",
    "perf_kpi.row.irr_quality": "Qualit\u00e9 capteur irradiance",
    "perf_kpi.row.high_actions": "Actions priorit\u00e9 haute",
    "perf_kpi.row.clean_pr": "PR potentiel (sans arr\u00eats)",
    "perf_kpi.row.clean_pr.target": "Indicatif vs {design_pr}\u00a0% conception",
    "perf_kpi.target.pr": "\u2265 {target}\u00a0%",
    "perf_kpi.target.gte95": "\u2265 95\u00a0%",
    "perf_kpi.target.zero": "0",
    "perf_kpi.target.dash": "-",
    "perf_kpi.target.coherent": "Coh\u00e9rent",
    "perf_kpi.status.on_target": "Conforme",
    "perf_kpi.status.watch": "Surveillance",
    "perf_kpi.status.below_target": "Hors cible",
    "perf_kpi.status.reference": "R\u00e9f\u00e9rence",
    "perf_kpi.status.coherent": "Coh\u00e9rent",
    "perf_kpi.status.review_required": "V\u00e9rification requise",
    "perf_kpi.status.none": "Aucune",
    "perf_kpi.status.open": "Ouverte",
    "perf_kpi.status.indicative": "Sc\u00e9nario indicatif",

    # ── Data Quality ─────────────────────────────────────────────────────────
    "data_qual.title": "Qualit\u00e9 des Donn\u00e9es et Confiance en l\u2019Irradiance",
    "data_qual.kicker": "Qualit\u00e9 des entr\u00e9es",
    "data_qual.summary": "Revue de la compl\u00e9tude de la t\u00e9l\u00e9mesure et de la confiance en l\u2019irradiance.",
    "data_qual.commentary_title": "Interpr\u00e9tation ing\u00e9nierie",
    "data_qual.commentary.power_irr.good": (
        "La compl\u00e9tude de puissance est {power_pct} et la compl\u00e9tude d\u2019irradiance est {irr_pct}. "
        "Les deux valeurs sont \u00e0 ou au-dessus de la cible de 95\u00a0%, de sorte que les indicateurs "
        "d\u2019\u00e9nergie et de PR sont adapt\u00e9s \u00e0 l\u2019interpr\u00e9tation ing\u00e9nierie."
    ),
    "data_qual.commentary.power_irr.poor": (
        "La compl\u00e9tude de puissance est {power_pct} et la compl\u00e9tude d\u2019irradiance est {irr_pct}. "
        "Un ou les deux canaux restent en-de\u00e7\u00e0 de la cible de 95\u00a0%, de sorte que les valeurs KPI "
        "pendant les p\u00e9riodes de donn\u00e9es manquantes pr\u00e9sentent une incertitude \u00e9lev\u00e9e "
        "et ne doivent pas \u00eatre utilis\u00e9es \u00e0 des fins contractuelles sans r\u00e9cup\u00e9ration des lacunes."
    ),
    "data_qual.commentary.below95": (
        "{n_below95} onduleur(s) sont sous le seuil de 95\u00a0% de compl\u00e9tude de t\u00e9l\u00e9mesure "
        "et {n_below90} sous 90\u00a0%\u00a0; le canal le plus faible est {worst_inv} \u00e0 {worst_value}. "
        "Des lacunes persistantes sur un onduleur unique biaisent de mani\u00e8re disproportionn\u00e9e "
        "les m\u00e9triques de disponibilit\u00e9 et de fiabilit\u00e9."
    ),
    "data_qual.commentary.sarah_good": (
        "Par rapport \u00e0 SARAH_{name}, la corr\u00e9lation d\u2019irradiance mesur\u00e9e est {correlation} "
        "avec {suspect_pct} de lectures suspectes\u00a0; aucun biais mat\u00e9riel d\u2019irradiance n\u2019est visible."
    ),
    "data_qual.commentary.sarah_poor": (
        "Par rapport \u00e0 SARAH_{name}, la corr\u00e9lation d\u2019irradiance mesur\u00e9e est {correlation} "
        "avec {suspect_pct} de lectures suspectes\u00a0; un biais capteur reste plausible et doit \u00eatre "
        "v\u00e9rifi\u00e9 sur le terrain."
    ),
    "data_qual.commentary.no_sarah": (
        "Aucune comparaison SARAH n\u2019est disponible, le rapport se fonde donc uniquement sur la compl\u00e9tude "
        "et les contr\u00f4les de coh\u00e9rence de l\u2019irradiance mesur\u00e9e."
    ),
    "data_qual.commentary.stuck": (
        "L\u2019analyse a d\u00e9tect\u00e9 et supprim\u00e9 les lectures SCADA gel\u00e9es/bloqu\u00e9es sur "
        "les {n_inverters} onduleurs \u2014 mode de d\u00e9faillance connu sur les syst\u00e8mes Modbus "
        "o\u00f9 le logger renvoie la derni\u00e8re valeur de registre valide plutot qu\u2019un vide de donn\u00e9es. "
        "Lorsque plusieurs onduleurs de diff\u00e9rents PTR partagent des fen\u00eatres identiques de donn\u00e9es "
        "manquantes, la cause racine est en amont (logger SCADA, lien de communication ou commutateur r\u00e9seau), "
        "pas sur le mat\u00e9riel d\u2019onduleur. "
        "Les capteurs d\u2019irradiance doivent \u00eatre valid\u00e9s mensuellement par rapport aux donn\u00e9es "
        "satellite PVGIS-SARAH3\u00a0; les pyranom\u00e8tres \u00e0 thermocouple d\u00e9rivent de +1\u00e0 3\u00a0%/an "
        "sans chauffage en climat humide (IEC\u00a061724-1 Classe A\u00a0: \u00e9talonnage annuel, nettoyage hebdomadaire)."
    ),
    "data_qual.kpi.power_completeness.label": "Compl\u00e9tude puissance",
    "data_qual.kpi.power_completeness.target": "Cible \u2265 95\u00a0%",
    "data_qual.kpi.irr_completeness.label": "Compl\u00e9tude irradiance",
    "data_qual.kpi.irr_completeness.target": "Cible \u2265 95\u00a0%",
    "data_qual.figure.telemetry.title": "Synth\u00e8se de la Compl\u00e9tude de T\u00e9l\u00e9mesure",
    "data_qual.figure.telemetry.caption": (
        "La compl\u00e9tude par onduleur est compar\u00e9e \u00e0 la couverture globale puissance et irradiance "
        "pour mettre en \u00e9vidence les risques de t\u00e9l\u00e9mesure les plus significatifs."
    ),

    # ── Data Quality Detail ──────────────────────────────────────────────────
    "data_qual_detail.title": "D\u00e9tail de la Qualit\u00e9 des Donn\u00e9es",
    "data_qual_detail.kicker": "Analyse des fen\u00eatres de lacunes",
    "data_qual_detail.summary": "Revue mensuelle des patterns de donn\u00e9es manquantes.",
    "data_qual_detail.commentary_title": "Interpr\u00e9tation d\u00e9taill\u00e9e",
    "data_qual_detail.finding.sitewide.title": "Coupure g\u00e9n\u00e9ralis\u00e9e du site",
    "data_qual_detail.finding.sitewide.body": (
        "{n_sitewide} p\u00e9riode(s) mensuelle(s) montrent une d\u00e9gradation g\u00e9n\u00e9ralis\u00e9e "
        "de la compl\u00e9tude sur l\u2019ensemble du site, plus compatible avec des interruptions logger, "
        "r\u00e9seau ou export qu\u2019avec des d\u00e9fauts d\u2019onduleurs isol\u00e9s."
    ),
    "data_qual_detail.finding.weakest.title": "Fen\u00eatre de compl\u00e9tude la plus faible",
    "data_qual_detail.finding.weakest.body": (
        "La fen\u00eatre de compl\u00e9tude mensuelle la plus faible se produit en {weakest_month}, "
        "o\u00f9 plusieurs onduleurs se d\u00e9gradent simultan\u00e9ment\u00a0; cette p\u00e9riode doit \u00eatre "
        "r\u00e9concili\u00e9e avec la r\u00e9cup\u00e9ration du tampon SCADA et l\u2019historique du logger."
    ),
    "data_qual_detail.figure.heatmap.title": "Carte Thermique de Compl\u00e9tude Mensuelle par Onduleur",
    "data_qual_detail.figure.heatmap.caption": (
        "Les bandes verticales de faible compl\u00e9tude indiquent des coupures g\u00e9n\u00e9ralis\u00e9es\u00a0; "
        "les bandes horizontales indiquent des lacunes de communication sp\u00e9cifiques \u00e0 un onduleur."
    ),

    # ── Irradiance Coherence ─────────────────────────────────────────────────
    "irr_coherence.title": "Analyse de Coh\u00e9rence des Donn\u00e9es d\u2019Irradiance",
    "irr_coherence.kicker": "Confiance capteur",
    "irr_coherence.summary": (
        "L\u2019irradiance mesur\u00e9e est contr\u00f4l\u00e9e par rapport \u00e0 SARAH pour d\u00e9tecter les biais, "
        "lectures suspectes et la fiabilit\u00e9 du d\u00e9nominateur de PR."
    ),
    "irr_coherence.commentary_title": "Interpr\u00e9tation ing\u00e9nierie",
    "irr_coherence.figure.monthly.title": "Irradiance Mesur\u00e9e vs Totaux Mensuels SARAH",
    "irr_coherence.figure.monthly.caption": (
        "L\u2019irradiation mensuelle mesur\u00e9e est compar\u00e9e \u00e0 chaque r\u00e9f\u00e9rence SARAH, "
        "avec le biais mensuel sur l\u2019axe secondaire."
    ),
    "irr_coherence.figure.scatter.title": "Nuage de Points Irradiance Mesur\u00e9e vs SARAH",
    "irr_coherence.figure.scatter.caption": (
        "Le nuage met en \u00e9vidence la corr\u00e9lation globale et l\u2019\u00e9tendue de la d\u00e9viation "
        "al\u00e9atoire ou syst\u00e9matique du capteur."
    ),
    "irr_coherence.table.title": "Synth\u00e8se de Coh\u00e9rence de l\u2019Irradiance",
    "irr_coherence.table.col.reference": "R\u00e9f\u00e9rence",
    "irr_coherence.table.col.correlation": "R (corr.)",
    "irr_coherence.table.col.ratio": "Ratio \u00b1 \u03c3",
    "irr_coherence.table.col.suspect_pct": "% suspect",
    "irr_coherence.table.col.gap_days": "Jours lacunes",
    "irr_coherence.table.col.status": "Statut",
    "irr_coherence.status.ok": "OK",
    "irr_coherence.status.review": "V\u00e9rifier",

    # ── Performance Overview ─────────────────────────────────────────────────
    "perf_overview.title": "Vue d\u2019Ensemble des Performances",
    "perf_overview.kicker": "\u00c9nergie et PR",
    "perf_overview.summary": (
        "Les tendances mensuelles et annuelles de PR comparent la production \u00e9nerg\u00e9tique "
        "avec la r\u00e9f\u00e9rence ajust\u00e9e m\u00e9t\u00e9o."
    ),
    "perf_overview.commentary_title": "Interpr\u00e9tation des performances",
    "perf_overview.commentary.yoy.decline": (
        "Le PR a \u00e9volu\u00e9 de {pr_first}\u00a0% \u00e0 {pr_last}\u00a0% d\u2019une ann\u00e9e \u00e0 l\u2019autre, "
        "tandis que l\u2019irradiation annuelle a vari\u00e9 de {irr_drop}\u00a0kWh/m\u00b2. "
        "Le d\u00e9clin du PR est plus important que ce que la seule variation d\u2019irradiation justifierait, "
        "ce qui confirme un m\u00e9canisme de perte op\u00e9rationnel."
    ),
    "perf_overview.commentary.yoy.aligned": (
        "Le PR a \u00e9volu\u00e9 de {pr_first}\u00a0% \u00e0 {pr_last}\u00a0% d\u2019une ann\u00e9e \u00e0 l\u2019autre, "
        "tandis que l\u2019irradiation annuelle a vari\u00e9 de {irr_drop}\u00a0kWh/m\u00b2. "
        "L\u2019\u00e9volution du PR est globalement align\u00e9e avec la variation d\u2019irradiation, "
        "la m\u00e9t\u00e9o restant un facteur pr\u00e9dominant de variance."
    ),
    "perf_overview.commentary.specific_yield": (
        "La production sp\u00e9cifique moyenne est {spec_yield}. "
        "La p\u00e9riode contient {critical_months} mois en-de\u00e7\u00e0 du seuil critique de 65\u00a0% "
        "et {warning_months} mois entre 65\u00a0% et {pr_target}\u00a0%."
    ),
    "perf_overview.commentary.summer": (
        "Si le PR estival reste faible alors que l\u2019irradiation est maximale, l\u2019encrassement, "
        "les arr\u00eats latents ou les pertes de qualit\u00e9 onduleur sont les causes probables \u2014 "
        "un d\u00e9clin de PR en saison s\u00e8che avec r\u00e9cup\u00e9ration compl\u00e8te apr\u00e8s les "
        "pluies d\u2019automne est la signature de l\u2019encrassement (2\u00e0 8\u00a0% typique pour "
        "le SO France). Le coefficient de temp\u00e9rature du CdTe \u221a\u20130,28\u00a0%/\u00b0C "
        "signifie que le PR estival devrait nominalement d\u00e9passer les r\u00e9f\u00e9rences c-Si\u00a0; "
        "si ce n\u2019est pas le cas, l\u2019encrassement ou la d\u00e9gradation \u00e9rode cet avantage thermique."
    ),
    "perf_overview.kpi.design_pr.label": "PR de conception",
    "perf_overview.kpi.avg_pr.label": "PR annuel moyen",
    "perf_overview.kpi.avg_pr.target": "Cible \u2265 78\u00a0%",
    "perf_overview.figure.monthly_pr.title": "\u00c9nergie Mensuelle, Irradiation et PR",
    "perf_overview.figure.monthly_pr.caption": (
        "Les barres d\u2019\u00e9nergie (gauche), la courbe d\u2019irradiation (droite, tirets verts) "
        "et la courbe de PR (droite, orange) sont superpos\u00e9es pour s\u00e9parer les variations "
        "m\u00e9t\u00e9orologiques des sous-performances op\u00e9rationnelles."
    ),
    "perf_overview.figure.daily_yield.title": "Production Sp\u00e9cifique Journali\u00e8re et Moyenne Mobile 30\u00a0jours",
    "perf_overview.figure.daily_yield.caption": (
        "La vue journali\u00e8re met en \u00e9vidence les p\u00e9riodes de faible production soutenue "
        "que les moyennes mensuelles peuvent masquer."
    ),
    "perf_overview.table.annual.title": "D\u00e9tail des Performances Annuelles",
    "perf_overview.table.annual.col.year": "Ann\u00e9e",
    "perf_overview.table.annual.col.pr": "PR",
    "perf_overview.table.annual.col.actual_energy": "\u00c9nergie r\u00e9elle",
    "perf_overview.table.annual.col.reference_energy": "\u00c9nergie de r\u00e9f\u00e9rence",
    "perf_overview.table.annual.col.gap": "\u00c9cart \u00e0 78\u00a0%",

    # ── Inverter Performance ─────────────────────────────────────────────────
    "inv_perf.title": "Comparaison des Onduleurs de la Flotte",
    "inv_perf.kicker": "Dispersion au niveau onduleur",
    "inv_perf.summary": "Comparaison de la flotte d\u2019onduleurs entre performance et disponibilit\u00e9.",
    "inv_perf.commentary_title": "Interpr\u00e9tation",
    "inv_perf.commentary": (
        "Le PR moyen de la flotte est {fleet_mean} avec un \u00e9cart-type de {fleet_std}. "
        "{low_both_count} onduleur(s) se situent dans le quadrant faible PR / faible disponibilit\u00e9, "
        "o\u00f9 la r\u00e9cup\u00e9ration du temps de fonctionnement est le premier levier. "
        "{low_pr_good_av_count} onduleur(s) ont un faible PR malgr\u00e9 une disponibilit\u00e9 acceptable, "
        "ce qui pointe vers un encrassement, des probl\u00e8mes de strings ou un comportement MPPT. "
        "Les onduleurs de ce deuxi\u00e8me groupe sont candidats prioritaires \u00e0 un scan I-V distant "
        "iSolarCloud avant toute intervention terrain \u2014 les causes les plus courantes sont un chargement "
        "in\u00e9gal des strings MPPT, une h\u00e9t\u00e9rog\u00e9n\u00e9it\u00e9 d\u2019encrassement ou "
        "un ombrage partiel. "
        "Un \u00e9cart persistant sup\u00e9rieur \u00e0 5\u00a0pp entre le meilleur et le moins bon onduleur "
        "sans lacune de disponibilit\u00e9 corr\u00e9l\u00e9e est la signature classique d\u2019une perte "
        "de qualit\u00e9 c\u00f4t\u00e9 DC."
    ),
    "inv_perf.kpi.fleet_mean_pr.label": "PR moyen flotte",
    "inv_perf.kpi.low_both.label": "Faible PR + faible disponibilit\u00e9",
    "inv_perf.kpi.low_pr_good_av.label": "Faible PR + bonne disponibilit\u00e9",
    "inv_perf.figure.scatter.title": "PR vs Disponibilit\u00e9",
    "inv_perf.figure.scatter.caption": (
        "Le nuage de points s\u00e9pare les pertes li\u00e9es aux arr\u00eats des sous-performances "
        "en cours de fonctionnement sur l\u2019ensemble de la flotte."
    ),
    "inv_perf.table.worst.title": "Onduleurs au PR le Plus Faible",
    "inv_perf.table.worst.col.inverter": "Onduleur",
    "inv_perf.table.worst.col.pr": "PR",
    "inv_perf.table.worst.col.availability": "Disponibilit\u00e9",

    # ── Specific Yield ───────────────────────────────────────────────────────
    "spec_yield.title": "Production Sp\u00e9cifique par Onduleur",
    "spec_yield.kicker": "D\u00e9tection des pertes de qualit\u00e9",
    "spec_yield.summary": (
        "Cartes thermiques mensuelles mettant en \u00e9vidence la sous-performance persistante "
        "par onduleur et la perte de qualit\u00e9 relative entre pairs."
    ),
    "spec_yield.commentary_title": "Interpr\u00e9tation",
    "spec_yield.commentary": (
        "Le PR moyen de la flotte est {fleet_mean}\u00a0; onduleurs les plus faibles\u00a0: {low_pr_names}. "
        "Les mois rouges persistants = en fonctionnement mais sous-performant, pas hors-ligne. "
        "{worst_dev_str}"
        "Les pics de production apr\u00e8s pluie confirment l\u2019encrassement\u00a0; un d\u00e9ficit stable "
        "tout au long de l\u2019ann\u00e9e insensible \u00e0 la pluie indique une perte \u00e9lectrique permanente "
        "(d\u00e9s\u00e9quilibre MPPT, strings court-circuit\u00e9s ou d\u00e9faut de bo\u00eete de jonction)."
    ),
    "spec_yield.figure.heatmap.title": "Cartes Thermiques de Production Sp\u00e9cifique et de PR",
    "spec_yield.figure.heatmap.caption": (
        "La vue sup\u00e9rieure s\u00e9pare la qualit\u00e9 de rendement relative entre pairs\u00a0; "
        "la vue inf\u00e9rieure conserve les arr\u00eats dans le PR afin que les deux m\u00e9canismes "
        "restent visibles."
    ),

    # ── Availability & Reliability ───────────────────────────────────────────
    "avail_rel.title": "Disponibilit\u00e9 et Fiabilit\u00e9",
    "avail_rel.kicker": "Temps de fonctionnement et r\u00e9currence des d\u00e9fauts",
    "avail_rel.summary": "Temps de fonctionnement de la flotte, exposition aux \u00e9v\u00e9nements r\u00e9seau et d\u00e9pistage de fiabilit\u00e9.",
    "avail_rel.commentary_title": "Interpr\u00e9tation",
    "avail_rel.commentary": (
        "La disponibilit\u00e9 moyenne de la flotte est {avail_mean}, avec {below_95_count} onduleur(s) "
        "sous le seuil de 95\u00a0% et {whole_site_events} \u00e9v\u00e9nement(s) de coupure simultan\u00e9e "
        "du site d\u00e9tect\u00e9s. "
        "Le temps moyen avant d\u00e9faillance des onduleurs avec des d\u00e9fauts enregistr\u00e9s est "
        "{fleet_mttf}. "
        "Pour les onduleurs avec un MTTF inf\u00e9rieur \u00e0 5 jours, l\u2019usure du contacteur AC "
        "(Fault\u00a0038) est le principal suspect \u2014 les comptages de trips sup\u00e9rieurs \u00e0 500/an "
        "provoquent une pit\u00e9faction des contacts qui emp\u00eache la reconnexion, lisible directement "
        "depuis le journal d\u2019\u00e9v\u00e9nements iSolarCloud avant toute visite terrain. "
        "Les coupures simultan\u00e9es sur l\u2019ensemble du site sont des signatures d\u2019\u00e9v\u00e9nements "
        "r\u00e9seau (surtension ou effacement) trait\u00e9es au niveau du transformateur HTA ou du DSO, "
        "pas au niveau de l\u2019onduleur. "
        "Les baisses de disponibilit\u00e9 exclusivement estivales limit\u00e9es aux heures de midi se "
        "r\u00e8solvent g\u00e9n\u00e9ralement en nettoyant les filtres d\u2019entr\u00e9e d\u2019air et en "
        "v\u00e9rifiant le fonctionnement du ventilateur (Fault\u00a0036/037)."
    ),
    "avail_rel.kpi.fleet_availability.label": "Disponibilit\u00e9 flotte",
    "avail_rel.kpi.fleet_availability.target": "Cible \u2265 95\u00a0%",
    "avail_rel.kpi.fleet_mttf.label": "MTTF moyen flotte",
    "avail_rel.kpi.fleet_mttf.target": "Cible \u2265 90 jours",
    "avail_rel.figure.trend.title": "Disponibilit\u00e9 Mensuelle du Site",
    "avail_rel.figure.trend.caption": (
        "La disponibilit\u00e9 mensuelle indique si l\u2019exposition aux pertes est persistante ou "
        "concentr\u00e9e sur un petit nombre d\u2019\u00e9v\u00e9nements."
    ),
    "avail_rel.table.units.title": "Onduleurs \u00e0 Plus Faible Disponibilit\u00e9 / Plus Fort Taux de D\u00e9faillance",
    "avail_rel.table.units.col.metric": "Indicateur",
    "avail_rel.table.units.col.value": "Valeur",
    "avail_rel.table.units.row.worst_av": "Onduleurs \u00e0 plus faible disponibilit\u00e9",
    "avail_rel.table.units.row.top_failures": "Plus forts taux de d\u00e9faillance",

    # ── Losses ───────────────────────────────────────────────────────────────
    "losses.title": "Pertes et R\u00e9cup\u00e9rabilit\u00e9",
    "losses.kicker": "Pont budget-r\u00e9el",
    "losses.summary": "Pont \u00e9nerg\u00e9tique budget-r\u00e9el et synth\u00e8se des pertes r\u00e9cup\u00e9rables.",
    "losses.commentary_title": "Interpr\u00e9tation",
    "losses.commentary.budget": (
        "Le budget ajust\u00e9 m\u00e9t\u00e9o est {weather_corrected} contre une production r\u00e9elle de {actual}."
    ),
    "losses.commentary.breakdown": (
        "La perte de disponibilit\u00e9 est {avail_loss}, la perte technique est {tech_loss}, "
        "et le terme r\u00e9siduel indique {residual_direction} de {residual}."
    ),
    "losses.residual.underperformance": "sous-performance",
    "losses.residual.overperformance": "surperformance",
    "losses.commentary.recovery": (
        "La perte de disponibilit\u00e9 reste le composant le plus r\u00e9cup\u00e9rable\u00a0: une am\u00e9lioration "
        "disciplin\u00e9e de la r\u00e9ponse maintenance pourrait r\u00e9cup\u00e9rer environ {recovery_mwh} "
        "sur une p\u00e9riode \u00e9quivalente, tandis que la perte technique r\u00e9siduelle n\u00e9cessite "
        "encore des contr\u00f4les terrain cibl\u00e9s pour l\u2019encrassement, les d\u00e9fauts de strings, "
        "le d\u00e9r\u00e9glage MPPT ou la r\u00e9sistance DC."
    ),
    "losses.commentary.grid": (
        "Pour le contexte du r\u00e9seau fran\u00e7ais\u00a0: les effacements RTE/Enedis sont une source "
        "croissante de perte non attribu\u00e9e \u2014 environ 3\u00a0TWh a \u00e9t\u00e9 effac\u00e9 "
        "nationalement en 2025 (en forte hausse par rapport \u00e0 2024). "
        "Les p\u00e9riodes d\u2019effacement non correctement journalis\u00e9es dans le SCADA apparaissent "
        "comme des pertes de disponibilit\u00e9 ou techniques inexplicables. "
        "Tout mois pr\u00e9sentant une baisse de PR inexplicable pendant les heures de pointe d\u2019export "
        "doit \u00eatre crois\u00e9 avec les registres d\u2019effacement du gestionnaire de r\u00e9seau avant "
        "d\u2019attribuer la perte \u00e0 un d\u00e9faut d\u2019onduleur."
    ),
    "losses.kpi.weather_corrected.label": "Budget ajust\u00e9 m\u00e9t\u00e9o",
    "losses.kpi.avail_loss.label": "Perte de disponibilit\u00e9",
    "losses.kpi.tech_loss.label": "Perte technique",
    "losses.figure.waterfall.title": "Cascade de Pertes \u00c9nerg\u00e9tiques",
    "losses.figure.waterfall.caption": (
        "La cascade convertit les principaux facteurs de perte en impact \u00e9nerg\u00e9tique "
        "et en priorit\u00e9 de r\u00e9cup\u00e9ration."
    ),
    "losses.figure.monthly_avail.title": "D\u00e9composition Mensuelle des Pertes de Disponibilit\u00e9",
    "losses.figure.monthly_avail.caption": (
        "Cette vue montre quels mois ont g\u00e9n\u00e9r\u00e9 le d\u00e9ficit de disponibilit\u00e9 "
        "sur la p\u00e9riode analys\u00e9e."
    ),
    "losses.table.top_opps.title": "Meilleures Opportunit\u00e9s de R\u00e9cup\u00e9ration \u00c9nerg\u00e9tique",
    "losses.table.top_opps.col.priority": "Priorit\u00e9",
    "losses.table.top_opps.col.category": "Cat\u00e9gorie",
    "losses.table.top_opps.col.loss_mwh": "Perte estim\u00e9e (MWh)",
    "losses.table.top_opps.col.loss_eur": "Perte estim\u00e9e (\u20ac)",
    "losses.table.top_opps.col.action": "Action",

    # ── Targeted Diagnostics ─────────────────────────────────────────────────
    "diag.title": "Diagnostics Cibl\u00e9s",
    "diag.kicker": "Comportement aux seuils",
    "diag.summary": "D\u00e9pistage du comportement au d\u00e9marrage et \u00e0 l\u2019arr\u00eat pour d\u00e9tecter les anomalies de seuil ou de r\u00e9veil.",
    "diag.commentary_title": "Interpr\u00e9tation",
    "diag.commentary.max_dev": (
        "La d\u00e9viation maximale de d\u00e9marrage relative \u00e0 la flotte est {max_start} et la d\u00e9viation "
        "maximale d\u2019arr\u00eat est {max_stop}. "
        "Les signatures persistantes de d\u00e9marrage tardif / arr\u00eat pr\u00e9coce restent un d\u00e9pistage "
        "efficace des seuils d\u2019onduleurs non harmonis\u00e9s."
    ),
    "diag.commentary.large_dev": (
        "Les d\u00e9viations au-del\u00e0 d\u2019environ 15 minutes ne peuvent pas \u00eatre expliqu\u00e9es "
        "par le seul bruit et restent compatibles avec des seuils de tension de d\u00e9marrage \u00e9lev\u00e9s, "
        "une sensibilit\u00e9 au r\u00e9veil ou des trips locaux r\u00e9currents."
    ),
    "diag.commentary.contained_dev": (
        "Les d\u00e9viations de d\u00e9marrage/arr\u00eat sont pr\u00e9sentes mais relativement contenues, "
        "elles restent donc une probl\u00e9matique secondaire par rapport aux pertes dominantes de "
        "disponibilit\u00e9 et de PR."
    ),
    "diag.commentary.red_outliers": (
        "Les valeurs aberrantes cod\u00e9es en rouge au-del\u00e0 de 15 minutes sont {flagged_red}\u00a0; "
        "ces unit\u00e9s justifient une revue de configuration avant toute intervention mat\u00e9rielle."
    ),
    "diag.commentary.amber_zone": (
        "Les d\u00e9viations en zone ambre entre 8 et 15 minutes restent visibles sur {flagged_amber}\u00a0; "
        "ces unit\u00e9s doivent \u00eatre surveill\u00e9es pour une persistance saisonni\u00e8re."
    ),
    "diag.commentary.late_start": (
        "Des signatures de d\u00e9marrage tardif plus prononc\u00e9es en hiver qu\u2019en \u00e9t\u00e9 "
        "indiquent que le seuil de d\u00e9marrage MPPT est r\u00e9gl\u00e9 trop haut (Fault\u00a0601) \u2014 "
        "ajustable via iSolarCloud \u00e0 0,5\u00a0% de la puissance nominale. "
        "Les d\u00e9viations d\u2019arr\u00eat pr\u00e9coce au cr\u00e9puscule refl\u00e8tent g\u00e9n\u00e9ralement "
        "la tension de string chutant sous le minimum MPPT de 200\u00a0V, le plus souvent "
        "en raison d\u2019un ombrage partiel."
    ),
    "diag.figure.start_stop.title": "D\u00e9viation de D\u00e9marrage et d\u2019Arr\u00eat",
    "diag.figure.start_stop.caption": (
        "Les d\u00e9viations de d\u00e9marrage/arr\u00eat mettent en \u00e9vidence la non-uniformit\u00e9 "
        "des seuils, la sensibilit\u00e9 au r\u00e9veil et les anomalies de commutation r\u00e9currentes."
    ),

    # ── Conclusions ──────────────────────────────────────────────────────────
    "conclusions.title": "Conclusions et Recommandations",
    "conclusions.kicker": "Synth\u00e8se",
    "conclusions.summary": "Conclusions techniques consolid\u00e9es et prochaines actions recommand\u00e9es.",
    "conclusions.commentary_title": "Conclusion",
    "conclusions.commentary.main": (
        "Le site cl\u00f4ture la p\u00e9riode \u00e0 {mean_pr} de PR moyen et {fleet_av} de disponibilit\u00e9 "
        "moyenne. Les m\u00e9canismes de perte dominants restent op\u00e9rationnels plut\u00f4t que "
        "purement m\u00e9t\u00e9orologiques."
    ),
    "conclusions.commentary.recovery": (
        "Les \u00e9v\u00e9nements g\u00e9n\u00e9ralis\u00e9s, les onduleurs sous-performants et la cascade "
        "indiquent tous une \u00e9nergie r\u00e9cup\u00e9rable plut\u00f4t qu\u2019un effet m\u00e9t\u00e9o "
        "irr\u00e9ductible. "
        "La perte de disponibilit\u00e9 reste {avail_loss} et la perte technique reste {tech_loss}."
    ),
    "conclusions.commentary.data_quality": (
        "La qualit\u00e9 des donn\u00e9es reste ad\u00e9quate pour le triage ing\u00e9nierie mais pas parfaite\u00a0: "
        "la compl\u00e9tude de puissance est {power_pct} et la compl\u00e9tude d\u2019irradiance est {irr_pct}."
    ),
    "conclusions.finding.recommended_action": "Action recommand\u00e9e\u00a0: {action}",
    "conclusions.kpi.avg_pr.label": "PR moyen",
    "conclusions.kpi.avg_pr.target": "Cible \u2265 78\u00a0%",
    "conclusions.kpi.fleet_av.label": "Disponibilit\u00e9 flotte",
    "conclusions.kpi.fleet_av.target": "Cible \u2265 95\u00a0%",
    "conclusions.kpi.high_actions.label": "Actions priorit\u00e9 haute",
    "conclusions.finding.no_critical.title": "Aucune action critique",
    "conclusions.finding.no_critical.body": (
        "Aucune action corrective \u00e0 haute priorit\u00e9 n\u2019a \u00e9t\u00e9 g\u00e9n\u00e9r\u00e9e "
        "par les seuils actuels."
    ),

    # ── Action Punchlist ─────────────────────────────────────────────────────
    "punchlist.title": "Liste d\u2019Actions Correctives",
    "punchlist.kicker": "Registre des actions correctives",
    "punchlist.summary": "Registre complet des actions pour la planification de maintenance et le suivi client.",
    "punchlist.commentary_title": "Synth\u00e8se du registre d\u2019actions",
    "punchlist.commentary": (
        "La liste contient {n_actions} actions class\u00e9es par priorit\u00e9 et impact \u00e9nerg\u00e9tique estim\u00e9. "
        "Les actions de haute priorit\u00e9 doivent \u00eatre trait\u00e9es comme premi\u00e8re phase corrective\u00a0; "
        "les actions de priorit\u00e9 moyenne restent pertinentes une fois les pertes dominantes de "
        "disponibilit\u00e9 et de PR stabilis\u00e9es."
    ),
    "punchlist.table.title": "Liste Compl\u00e8te des Actions Correctives",
    "punchlist.table.col.priority": "Priorit\u00e9",
    "punchlist.table.col.category": "Cat\u00e9gorie",
    "punchlist.table.col.loss_mwh": "Perte estim\u00e9e (MWh)",
    "punchlist.table.col.loss_eur": "Perte estim\u00e9e (\u20ac)",
    "punchlist.table.col.issue": "Probl\u00e8me",
    "punchlist.table.col.action": "Action recommand\u00e9e",

    # ── Technology Risk Register ─────────────────────────────────────────────
    "tech_risk.title": "Registre des Risques Technologiques",
    "tech_risk.kicker": "Sungrow SG250HX & First Solar CdTe",
    "tech_risk.summary": (
        "Principaux modes de d\u00e9faillance, risques de performance et actions de diagnostic "
        "sp\u00e9cifiques aux technologies d\u2019onduleur et de module d\u00e9ploy\u00e9es sur ce site."
    ),
    "tech_risk.commentary_title": "Contexte des risques",
    "tech_risk.commentary.register": (
        "Ce registre consolide {high_count} risques HAUTE priorit\u00e9 et {med_count} risques MOYENNE "
        "priorit\u00e9 d\u00e9riv\u00e9s de l\u2019exp\u00e9rience terrain sur des sites PV comparables en France, "
        "de la documentation Sungrow EMEA sur les d\u00e9fauts, des publications techniques First Solar "
        "et des normes de surveillance NREL/AIE."
    ),
    "tech_risk.commentary.context": (
        "Les \u00e9l\u00e9ments HAUTE priorit\u00e9 repr\u00e9sentent des modes de d\u00e9faillance avec "
        "des pr\u00e9c\u00e9dents terrain confirm\u00e9s et un potentiel de perte \u00e9nerg\u00e9tique "
        "mat\u00e9riel pouvant persister sans inspection cibl\u00e9e. "
        "Les \u00e9l\u00e9ments MOYENNE priorit\u00e9 sont des points de surveillance op\u00e9rationnels. "
        "Les \u00e9l\u00e9ments INFO fournissent un contexte de r\u00e9f\u00e9rence pour \u00e9viter "
        "d\u2019interpr\u00e9ter \u00e0 tort le comportement normal de la technologie comme des d\u00e9fauts."
    ),
    "tech_risk.table.title": "Registre des Risques \u2014 Sungrow SG250HX & First Solar S\u00e9rie\u00a06",
    "tech_risk.table.col.priority": "Priorit\u00e9",
    "tech_risk.table.col.equipment": "\u00c9quipement",
    "tech_risk.table.col.risk": "Risque / \u00c0 surveiller",
    "tech_risk.table.col.action": "Diagnostic / Action",
    "tech_risk.priority.high": "HAUTE",
    "tech_risk.priority.medium": "MOYENNE",
    "tech_risk.priority.info": "INFO",
    # Risk rows — Risk column
    "tech_risk.row.ac_relay.risk": (
        "Usure du contacteur AC (Fault\u00a0038) \u2014 les sites \u00e0 fort taux de trips d\u00e9veloppent "
        "des contacts pit\u00e9s\u00a0; l\u2019onduleur ne parvient pas \u00e0 se reconnecter apr\u00e8s un trip."
    ),
    "tech_risk.row.dc_insulation.risk": (
        "D\u00e9faut d\u2019isolation DC (Fault\u00a0039) \u2014 d\u00e9clench\u00e9 apr\u00e8s pluie si Riso string "
        "< 50\u00a0k\u03a9. Risque \u00e9lev\u00e9 avec des connecteurs MC4 tiers ou des c\u00e2bles "
        "pinc\u00e9s sous les rails de tracker."
    ),
    "tech_risk.row.mppt_wiring.risk": (
        "Erreur de c\u00e2blage MPPT \u2014 PR d\u2019un seul onduleur persistant 10\u201315\u00a0% "
        "sous la flotte sans alarmes de d\u00e9faut et sans variation saisonni\u00e8re. "
        "Peut persister des ann\u00e9es sans \u00eatre d\u00e9tect\u00e9."
    ),
    "tech_risk.row.pid.risk": (
        "Corrosion PID / TCO \u2014 perte de puissance sur les modules en bout de string n\u00e9gatif "
        "due \u00e0 la migration du sodium et \u00e0 la corrosion TCO. "
        "Risque \u00e9lev\u00e9 dans les syst\u00e8mes haute tension non mis \u00e0 la terre."
    ),
    "tech_risk.row.pr_decline.risk": (
        "D\u00e9clin du PR d\u00e9passant le taux garanti \u2014 garanti 0,55\u00a0%/an (contact Cu) "
        "ou 0,2\u00a0%/an (CuRe). Un d\u00e9clin du PR flotte >1\u00a0%/an n\u00e9cessite une "
        "investigation prioritaire."
    ),
    "tech_risk.row.thermal.risk": (
        "Surtemp\u00e9rature thermique (Faults\u00a0036/037) \u2014 trips \u00e0 mi-journ\u00e9e estivale "
        "si l\u2019ambiant d\u00e9passe 45\u00b0C pr\u00e8s du coffret, roulements de ventilateur bloqu\u00e9s "
        "ou filtres d\u2019entr\u00e9e d\u2019air obstru\u00e9s."
    ),
    "tech_risk.row.curtailment.risk": (
        "Effacement r\u00e9seau fran\u00e7ais non journalis\u00e9 (SUN-014) \u2014 effacements RTE/Enedis "
        "apparaissant comme des baisses de PR inexplicables. ~3\u00a0TWh effac\u00e9s en France en 2025, "
        "en forte hausse."
    ),
    "tech_risk.row.irr_drift.risk": (
        "D\u00e9rive du capteur d\u2019irradiance \u2014 les pyranom\u00e8tres \u00e0 thermocouple d\u00e9rivent "
        "de +1\u00e0 3\u00a0%/an sans chauffage en climat humide, faisant appara\u00eetre le PR en d\u00e9clin. "
        "Les cellules de r\u00e9f\u00e9rence surestiment l\u2019irradiation journali\u00e8re de >2\u00a0%."
    ),
    "tech_risk.row.hot_spot.risk": (
        "Difficult\u00e9 de d\u00e9tection des points chauds \u2014 la structure monolithique CdTe et "
        "l\u2019encapsulation verre-verre produisent des gradients de temp\u00e9rature de surface "
        "plus faibles que le c-Si\u00a0; les inspections IR standard les manquent."
    ),
    "tech_risk.row.cdte_temp.risk": (
        "Avantage du coefficient de temp\u00e9rature CdTe \u2014 coeff. Pmax \u22120,28\u00a0%/\u00b0C "
        "vs c-Si \u22120,35 \u00e0 \u22120,50\u00a0%/\u00b0C. Le PR estival doit d\u00e9passer les "
        "r\u00e9f\u00e9rences c-Si \u2014 c\u2019est attendu, pas un d\u00e9faut."
    ),
    "tech_risk.row.iv_curve.risk": (
        "Scan I-V distant iSolarCloud \u2014 diagnostic complet identifiant poussi\u00e8re, fissures, "
        "courts-circuits de diodes, d\u00e9s\u00e9quilibre MPPT et att\u00e9nuation PID en ~15 minutes "
        "avec <0,5\u00a0% de pr\u00e9cision."
    ),
    "tech_risk.row.clipping.risk": (
        "Sous-estimation des pertes par \u00e9cr\u00eatage \u2014 au ratio DC/AC de 1,27 (ce site), "
        "l\u2019\u00e9cr\u00eatage se produit ~3\u00e0 4\u00a0% des heures de fonctionnement annuelles. "
        "Les moyennes SCADA \u00e0 10 min masquent l\u2019ampleur r\u00e9elle de l\u2019\u00e9cr\u00eatage."
    ),
    # Risk rows — Action column
    "tech_risk.row.ac_relay.action": (
        "Extraire le comptage de trips depuis le journal d\u2019\u00e9v\u00e9nements iSolarCloud. "
        "Si >500 trips/an, remplacer le relais de fa\u00e7on pr\u00e9ventive. "
        "V\u00e9rifier les parafoudres dans le coffret BT pour court-circuit de terre. "
        "\u00c9couter le claquement du relais au red\u00e9marrage \u2014 absent = relais d\u00e9fectueux."
    ),
    "tech_risk.row.dc_insulation.action": (
        "Test d\u2019isolation string par string pour localiser le string affect\u00e9. "
        "Megger \u00e0 1\u00a0000\u00a0V DC (cible >1\u00a0M\u03a9). "
        "Remplacer les connecteurs MC4 tiers par un type compatible OEM."
    ),
    "tech_risk.row.mppt_wiring.action": (
        "Auditer les strings par MPPT vs le sch\u00e9ma unifilaire. "
        "Calculer la puissance DC par MPPT vs l\u2019entr\u00e9e nominale. "
        "Lancer un scan I-V iSolarCloud pour identifier les canaux MPPT anormaux."
    ),
    "tech_risk.row.pid.action": (
        "Campagne d\u2019imagerie EL prioritisant les modules en bout de string n\u00e9gatif. "
        "Courbe I-V pour la signature de perte de Voc et de facteur de forme. "
        "V\u00e9rifier l\u2019int\u00e9grit\u00e9 du joint de bord sur les modules suspects."
    ),
    "tech_risk.row.pr_decline.action": (
        "Tests EL/IV sur un \u00e9chantillon de modules. Revoir le journal d\u2019encrassement et "
        "les registres de nettoyage. V\u00e9rifier la tendance du rendement onduleur. "
        "Comparer le capteur d\u2019irradiance vs PVGIS-SARAH3 pour d\u00e9tecter une d\u00e9rive capteur."
    ),
    "tech_risk.row.thermal.action": (
        "Inspecter les ventilateurs et filtres d\u2019air \u00e0 chaque visite de maintenance. "
        "D\u00e9gagement de 500\u00a0mm requis autour de l\u2019enveloppe. "
        "Installer un auvent de protection si l\u2019ambiant d\u00e9passe r\u00e9guli\u00e8rement 45\u00b0C en \u00e9t\u00e9."
    ),
    "tech_risk.row.curtailment.action": (
        "V\u00e9rifier que les horodatages des ordres d\u2019effacement sont journalis\u00e9s dans le SCADA. "
        "Croiser avec les registres du gestionnaire de r\u00e9seau pour les mois \u00e0 baisses de PR "
        "inexplicables. Exclure les p\u00e9riodes effac\u00e9es du PR contractuel."
    ),
    "tech_risk.row.irr_drift.action": (
        "Comparaison mensuelle de l\u2019irradiation sur site vs PVGIS-SARAH3. "
        "\u00c9talonnage annuel du capteur (IEC\u00a061724-1 Classe\u00a0A). Journal de nettoyage hebdomadaire. "
        "Remplacer les instruments Classe\u00a0C par ISO\u00a09060 Classe\u00a0A pour le PR contractuel."
    ),
    "tech_risk.row.hot_spot.action": (
        "Utiliser une cam\u00e9ra IR haute sensibilit\u00e9 (NETD <50\u00a0mK). "
        "Effectuer l\u2019inspection thermographique \u00e0 >600\u00a0W/m\u00b2 d\u2019irradiance. "
        "Confirmer par mesure de perte du facteur de forme en courbe I-V sur les modules suspects."
    ),
    "tech_risk.row.cdte_temp.action": (
        "Ne pas appliquer les r\u00e9f\u00e9rences PR c-Si aux installations CdTe en conditions chaudes. "
        "Un PR estival se rapprochant des niveaux c-Si peut indiquer une d\u00e9gradation du module "
        "ou un encrassement \u00e9rodant l\u2019avantage thermique."
    ),
    "tech_risk.row.iv_curve.action": (
        "Planifier un scan I-V distant via iSolarCloud avant toute intervention terrain pour "
        "sous-performance inexplicable. Les r\u00e9sultats localisent les strings affect\u00e9s sans visite site."
    ),
    "tech_risk.row.clipping.action": (
        "Configurer le SCADA au pas de 5\u00a0min pour capturer pr\u00e9cis\u00e9ment l\u2019\u00e9cr\u00eatage. "
        "Appliquer un facteur de correction d\u2019\u00e9cr\u00eatage lors de la comparaison du PR SCADA "
        "avec le mod\u00e8le de production horaire."
    ),

    # ── Appendix — MTTF Overview ─────────────────────────────────────────────
    "app_mttf_overview.title": "Annexe - Vue d\u2019Ensemble de la Fiabilit\u00e9",
    "app_mttf_overview.summary": "Diagnostics MTTF et comptage de d\u00e9faillances \u00e0 l\u2019\u00e9chelle de la flotte pour la planification de maintenance.",
    "app_mttf_overview.commentary_title": "Interpr\u00e9tation de la fiabilit\u00e9",
    "app_mttf_overview.commentary.main": (
        "Le MTTF moyen de la flotte est {fleet_mttf} contre le crit\u00e8re de 90 jours utilis\u00e9 pour "
        "le d\u00e9pistage maintenance. {high_fault} onduleur(s) d\u00e9passent 100 \u00e9v\u00e9nements de "
        "d\u00e9faut et {med_fault} suppl\u00e9mentaire(s) se situent dans la plage 30\u201330 d\u00e9fauts."
    ),
    "app_mttf_overview.commentary.worst": "Les unit\u00e9s \u00e0 d\u00e9fauts r\u00e9currents les plus \u00e9lev\u00e9s sont {worst_faults}.",
    "app_mttf_overview.commentary.ranking": (
        "Les graphiques de classement d\u00e9pistent la gravit\u00e9 de la r\u00e9currence, tandis que le "
        "tableau de d\u00e9tail suivant pr\u00e9serve la tra\u00e7abilit\u00e9 de tous les onduleurs n\u00e9cessaire "
        "\u00e0 la planification de maintenance."
    ),
    "app_mttf_overview.figure.failures.title": "Classement par Nombre de D\u00e9faillances",
    "app_mttf_overview.figure.failures.caption": (
        "Les plus forts comptages d\u2019\u00e9v\u00e9nements de d\u00e9faut identifient les unit\u00e9s "
        "n\u00e9cessitant une analyse imm\u00e9diate des causes racines."
    ),
    "app_mttf_overview.figure.mttf.title": "Temps Moyen Avant D\u00e9faillance les Plus Faibles",
    "app_mttf_overview.figure.mttf.caption": (
        "Le MTTF met en \u00e9vidence les unit\u00e9s au taux de r\u00e9currence le plus rapide, "
        "pas seulement le plus grand comptage vie."
    ),
    "app_mttf_overview.note": (
        "Le SCADA confirme les patterns de r\u00e9currence mais ne peut pas identifier les modes de "
        "trip exacts sans les exports d\u2019alarmes et codes de d\u00e9faut du constructeur."
    ),

    # ── Appendix — MTTF Detail ───────────────────────────────────────────────
    "app_mttf_detail.title": "Annexe - D\u00e9tail MTTF - Tous Onduleurs",
    "app_mttf_detail.summary": "D\u00e9tail de fiabilit\u00e9 de tous les onduleurs conserv\u00e9 pour la tra\u00e7abilit\u00e9 ing\u00e9nierie.",
    "app_mttf_detail.table.title": "D\u00e9tail MTTF - Tous Onduleurs",
    "app_mttf_detail.table.col.inverter": "Onduleur",
    "app_mttf_detail.table.col.faults": "D\u00e9fauts",
    "app_mttf_detail.table.col.run_hrs": "Heures fonct.",
    "app_mttf_detail.table.col.mttf_d": "MTTF (j)",
    "app_mttf_detail.table.col.mttf_h": "MTTF (h)",
    "app_mttf_detail.table.col.status": "Statut",
    "app_mttf_detail.table.caption": (
        "Critique = plus de 100 \u00e9v\u00e9nements de d\u00e9faut sur la p\u00e9riode analys\u00e9e\u00a0; "
        "Avertissement = 31 \u00e0 100 \u00e9v\u00e9nements."
    ),
    "app_mttf_detail.status.critical": "Critique",
    "app_mttf_detail.status.warning": "Avertissement",
    "app_mttf_detail.status.normal": "Normal",

    # ── Appendix — Weather Correlation ───────────────────────────────────────
    "app_weather.title": "Annexe - Corr\u00e9lation M\u00e9t\u00e9orologique",
    "app_weather.summary": (
        "Diagnostics contextuels m\u00e9t\u00e9o secondaires conserv\u00e9s en annexe pour pr\u00e9server "
        "la lisibilit\u00e9 du corps principal."
    ),
    "app_weather.commentary_title": "Interpr\u00e9tation du contexte m\u00e9t\u00e9o",
    "app_weather.figure.title": "PR vs Temp\u00e9rature et Pluviom\u00e9trie",
    "app_weather.figure.caption": (
        "Le PR mensuel est compar\u00e9 \u00e0 la pluviom\u00e9trie et \u00e0 la temp\u00e9rature, "
        "avec une vue journali\u00e8re color\u00e9e par la temp\u00e9rature."
    ),

    # ── Appendix — Clipping ──────────────────────────────────────────────────
    "app_clipping.title": "Annexe - Analyse de l\u2019\u00c9cr\u00eatage",
    "app_clipping.summary": "Diagnostics de quasi-\u00e9cr\u00eatage pour la revue du chargement onduleur.",
    "app_clipping.commentary_title": "Interpr\u00e9tation de l\u2019\u00e9cr\u00eatage",
    "app_clipping.commentary": (
        "Le quasi-\u00e9cr\u00eatage se produit sur {near_pct} des intervalles diurnes valides au niveau "
        "du site, ce qui est utile pour d\u00e9pister l\u2019exposition possible au plafond AC "
        "pendant les p\u00e9riodes de forte irradiance."
    ),
    "app_clipping.figure.title": "Diagnostics d\u2019\u00c9cr\u00eatage",
    "app_clipping.figure.caption": (
        "Les vues de distribution de puissance, bin d\u2019irradiance et top onduleurs d\u00e9pistent "
        "o\u00f9 le fonctionnement proche du plafond est concentr\u00e9."
    ),

    # ── Appendix — Limitations ───────────────────────────────────────────────
    "app_limitations.title": "Annexe - P\u00e9rim\u00e8tre Analytique et Limites des Donn\u00e9es",
    "app_limitations.summary": (
        "Synth\u00e8se du p\u00e9rim\u00e8tre analytique r\u00e9alis\u00e9 et des principales contraintes de "
        "donn\u00e9es affectant l\u2019interpr\u00e9tation."
    ),
    "app_limitations.table.scope.title": "P\u00e9rim\u00e8tre Analytique R\u00e9alis\u00e9",
    "app_limitations.table.scope.col.activity": "Activit\u00e9",
    "app_limitations.table.scope.col.status": "Statut",
    "app_limitations.table.scope.col.notes": "Notes",
    "app_limitations.table.constraints.title": "Contraintes Analytiques",
    "app_limitations.table.constraints.col.analysis": "Analyse",
    "app_limitations.table.constraints.col.status": "Statut",
    "app_limitations.table.constraints.col.notes": "Notes",
    "app_limitations.table.priority.title": "Instantan\u00e9 des Actions Prioritaires",
    "app_limitations.table.priority.col.priority": "Priorit\u00e9",
    "app_limitations.table.priority.col.category": "Cat\u00e9gorie",
    "app_limitations.table.priority.col.estimated_loss": "Perte estim\u00e9e",
    "app_limitations.table.priority.col.action": "Action recommand\u00e9e",
    # Scope rows
    "app_limitations.scope.data_avail.activity": "\u00c9valuation de la disponibilit\u00e9 des donn\u00e9es",
    "app_limitations.scope.data_avail.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.data_avail.notes": "Compl\u00e9tude de t\u00e9l\u00e9mesure par onduleur et au niveau site revu\u00e9e.",
    "app_limitations.scope.pr.activity": "\u00c9valuation du ratio de performance",
    "app_limitations.scope.pr.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.pr.notes": "PR mensuel et annuel calcul\u00e9 sur la base DC-kWc IEC\u00a061724.",
    "app_limitations.scope.irr.activity": "Coh\u00e9rence irradiance (SARAH-3)",
    "app_limitations.scope.irr.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.irr.notes": (
        "Irradiance sur site contr\u00f4l\u00e9e par rapport \u00e0 la r\u00e9f\u00e9rence SARAH, "
        "y compris le d\u00e9pistage des biais et des lectures suspectes."
    ),
    "app_limitations.scope.avail.activity": "Revue de disponibilit\u00e9 et fiabilit\u00e9",
    "app_limitations.scope.avail.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.avail.notes": "Temps de fonctionnement flotte, disponibilit\u00e9 par onduleur et r\u00e9currence des d\u00e9fauts d\u00e9pist\u00e9s.",
    "app_limitations.scope.loss.activity": "Attribution des pertes",
    "app_limitations.scope.loss.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.loss.notes": "Budget, correction m\u00e9t\u00e9o, perte de disponibilit\u00e9, perte technique et r\u00e9sidu revu\u00e9s.",
    "app_limitations.scope.yield.activity": "Production sp\u00e9cifique par onduleur",
    "app_limitations.scope.yield.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.yield.notes": "Cartes thermiques mensuelles par onduleur revu\u00e9es pour patterns de sous-performance r\u00e9currents.",
    "app_limitations.scope.startstop.activity": "D\u00e9pistage signatures d\u00e9marrage/arr\u00eat",
    "app_limitations.scope.startstop.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.startstop.notes": "D\u00e9viations de timing de r\u00e9veil et d\u2019extinction relatives \u00e0 la flotte d\u00e9pist\u00e9es pour anomalies de seuil.",
    "app_limitations.scope.weather.activity": "Revue de corr\u00e9lation m\u00e9t\u00e9o",
    "app_limitations.scope.weather.status": "R\u00e9alis\u00e9",
    "app_limitations.scope.weather.notes": "Contexte pluviom\u00e9trique et thermique pris en compte dans le diagnostic.",
    # Constraint rows
    "app_limitations.constraint.acdc.analysis": "Rendement AC/DC onduleur",
    "app_limitations.constraint.acdc.status": "Non possible",
    "app_limitations.constraint.acdc.notes": "Aucun canal de courant DC ou puissance DC disponible dans l\u2019export.",
    "app_limitations.constraint.string.analysis": "D\u00e9tection de d\u00e9fauts au niveau string",
    "app_limitations.constraint.string.status": "Non possible",
    "app_limitations.constraint.string.notes": "L\u2019export SCADA est limit\u00e9 \u00e0 la production AC au niveau onduleur.",
    "app_limitations.constraint.transients.analysis": "Transitoires courts",
    "app_limitations.constraint.transients.status": "Limit\u00e9",
    "app_limitations.constraint.transients.notes": "Le pas d\u2019\u00e9chantillonnage de 10 minutes est trop grossier pour l\u2019isolation des d\u00e9fauts sous-intervalle.",
    "app_limitations.constraint.downtime.analysis": "Cause racine des arr\u00eats",
    "app_limitations.constraint.downtime.status": "Limit\u00e9",
    "app_limitations.constraint.downtime.notes": "Les canaux d\u2019alarmes et codes de d\u00e9faut sont absents, les trips sont donc class\u00e9s indirectement.",
    "app_limitations.constraint.curtailment.analysis": "Certitude d\u2019effacement",
    "app_limitations.constraint.curtailment.status": "Limit\u00e9",
    "app_limitations.constraint.curtailment.notes": "Sans indicateurs explicites de limitation d\u2019export, l\u2019effacement reste heuristique.",
    "app_limitations.constraint.degradation.analysis": "Certitude de d\u00e9gradation",
    "app_limitations.constraint.degradation.status": "Limit\u00e9",
    "app_limitations.constraint.degradation.notes": "L\u2019horizon temporel disponible est trop court pour une estimation robuste de la d\u00e9gradation \u00e0 long terme.",
    "app_limitations.constraint.soiling.analysis": "Quantification de l\u2019encrassement",
    "app_limitations.constraint.soiling.status": "Non possible",
    "app_limitations.constraint.soiling.notes": "Aucun capteur d\u2019encrassement d\u00e9di\u00e9 ni jeu de donn\u00e9es I-V disponible pour isoler les taux d\u2019accumulation.",
}
