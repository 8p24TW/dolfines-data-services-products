from __future__ import annotations

from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import re

import matplotlib.dates as mdates
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd


def _fmt_pct(value: float | int | None, digits: int = 1) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}%"


def _fmt_num(value: float | int | None, digits: int = 0, suffix: str = "") -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:,.{digits}f}{suffix}"


def _fmt_eur(value: float | int | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"EUR {value:,.0f}"


def _fmt_eur_per_year(value: float | int | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"EUR {value:,.0f}/yr"


def _figure_block(charts: dict, chart_id: str, title: str, caption: str, width: str = "full") -> dict | None:
    meta = charts.get(chart_id)
    if not meta:
        return None
    return {
        "title": title,
        "caption": caption,
        "src": Path(meta["path"]).as_uri(),
        "width": width,
        "alt": meta.get("alt", title),
    }


def _table_block(title: str, columns: list[str], rows: list[dict], caption: str = "", appendix_only: bool = False) -> dict:
    return {
        "title": title,
        "columns": columns,
        "rows": rows,
        "caption": caption,
        "appendix_only": appendix_only,
    }


def _kpi(label: str, value: str, target: str = "", status: str = "neutral", subtext: str = "") -> dict:
    return {
        "label": label,
        "value": value,
        "target": target,
        "status": status,
        "subtext": subtext,
    }


def _sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", str(name))
    return (int(match.group(1)), str(name)) if match else (9999, str(name))


def _haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat_b - lat_a)
    d_lon = radians(lon_b - lon_a)
    a = sin(d_lat / 2.0) ** 2 + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lon / 2.0) ** 2
    return 2.0 * earth_radius_km * asin(sqrt(a))


class WindChartFactory:
    def __init__(self, *, config: dict, analysis: dict, assets_dir: Path) -> None:
        self.config = config
        self.analysis = analysis
        self.assets_dir = assets_dir
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.tokens = config["style_tokens"]["colors"]
        self.sizes = config["style_tokens"]["chart"]
        plt.rcParams.update(
            {
                "axes.titlesize": 12,
                "axes.labelsize": 10.5,
                "xtick.labelsize": 9.5,
                "ytick.labelsize": 9.5,
                "legend.fontsize": 8.8,
            }
        )

    def build_all(self) -> dict:
        charts = {}
        for builder in [
            self.chart_site_locator_map,
            self.chart_data_availability_overview,
            self.chart_data_availability_heatmap,
            self.chart_monthly_energy_cf,
            self.chart_daily_specific_yield,
            self.chart_fleet_comparison,
            self.chart_availability_trend,
            self.chart_waterfall,
            self.chart_monthly_availability_loss,
            self.chart_fleet_power_curve,
            self.chart_fault_duration_by_turbine,
        ]:
            result = builder()
            if result:
                charts[result["id"]] = result
        return charts

    def _apply_axes_style(self, ax) -> None:
        ax.set_facecolor("white")
        ax.grid(True, axis="y", color=self.tokens["border_grey"], alpha=0.45, linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(self.tokens["border_grey"])
        ax.spines["bottom"].set_color(self.tokens["border_grey"])
        ax.tick_params(colors=self.tokens["body_text"], labelsize=9)
        ax.title.set_color(self.tokens["primary_navy"])
        ax.xaxis.label.set_color(self.tokens["body_text"])
        ax.yaxis.label.set_color(self.tokens["body_text"])

    def _figure(self, size_key: str = "full", nrows: int = 1, ncols: int = 1):
        figsize = self.sizes[size_key]
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, constrained_layout=True)
        fig.patch.set_facecolor("white")
        return fig, axes

    def _save(self, fig, chart_id: str, alt: str) -> dict:
        path = self.assets_dir / f"{chart_id}.svg"
        fig.savefig(path, format="svg", dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return {"id": chart_id, "path": str(path), "alt": alt}

    def _save_png(self, fig, chart_id: str, alt: str) -> dict:
        path = self.assets_dir / f"{chart_id}.png"
        fig.savefig(path, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return {"id": chart_id, "path": str(path), "alt": alt}

    def chart_data_availability_overview(self) -> dict:
        completeness = self.analysis["data_quality"]["power_completeness"]
        items = sorted(completeness.items(), key=lambda item: _sort_key(item[0]))
        labels = [name for name, _ in items]
        values = [value for _, value in items]
        fig = plt.figure(figsize=(8.6, 4.9), constrained_layout=True)
        ax = fig.add_subplot(111)
        colors = [
            self.tokens["danger_red"] if value < 95 else self.tokens["warning_amber"] if value < 98 else self.tokens["secondary_slate_blue"]
            for value in values
        ]
        ax.barh(labels, values, color=colors, edgecolor="white")
        ax.axvline(98, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.1)
        ax.set_title("Per-Turbine Power Completeness", fontsize=11, fontweight="bold")
        ax.set_xlabel("Completeness (%)")
        ax.set_xlim(60, 100)
        ax.invert_yaxis()
        ax.grid(True, axis="x", color=self.tokens["border_grey"], alpha=0.45, linewidth=0.8)
        ax.grid(False, axis="y")
        self._apply_axes_style(ax)
        return self._save(fig, "data_availability_overview", "Per-turbine power completeness chart")

    def chart_data_availability_heatmap(self) -> dict | None:
        monthly = self.analysis["data_quality"]["monthly_power_completeness"]
        if monthly.empty:
            return None
        monthly = monthly.sort_index(axis=1, key=lambda cols: [_sort_key(item) for item in cols])
        fig = plt.figure(figsize=(7.2, 5.3), constrained_layout=True)
        ax = fig.add_subplot(111)
        cmap = LinearSegmentedColormap.from_list(
            "wind_dq",
            [self.tokens["danger_red"], self.tokens["accent_orange"], "#F4F6F8", self.tokens["secondary_slate_blue"]],
        )
        im = ax.imshow(monthly.T.values, aspect="auto", cmap=cmap, vmin=60, vmax=100)
        ax.set_title("Monthly Turbine Power Completeness Heat Map", fontsize=11, fontweight="bold")
        ax.set_yticks(range(len(monthly.columns)))
        ax.set_yticklabels(list(monthly.columns), fontsize=8)
        ax.set_xticks(range(len(monthly.index)))
        ax.set_xticklabels([ts.strftime("%b\n%y") for ts in monthly.index], fontsize=8)
        self._apply_axes_style(ax)
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="Completeness (%)")
        return self._save(fig, "data_availability_heatmap", "Monthly turbine power completeness heat map")

    def chart_monthly_energy_cf(self) -> dict:
        monthly = self.analysis["performance"]["monthly"]
        fig, ax1 = self._figure("full")
        ax1 = ax1 if not isinstance(ax1, np.ndarray) else ax1[0]
        ax2 = ax1.twinx()
        bars = ax1.bar(monthly.index, monthly["energy_mwh"], width=20, color=self.tokens["secondary_slate_blue"], alpha=0.9, label="Energy")
        wind_line = ax2.plot(
            monthly.index,
            monthly["wind_speed_ms"],
            color=self.tokens["accent_orange"],
            marker="o",
            linewidth=1.7,
            label="Mean wind speed",
        )[0]
        ax1.set_title("Monthly Energy And Mean Wind Speed", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Energy (MWh)")
        ax2.set_ylabel("Wind speed (m/s)")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax1)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color(self.tokens["border_grey"])
        ax2.tick_params(colors=self.tokens["body_text"], labelsize=8.5)
        ax1.legend([bars, wind_line], ["Energy", "Mean wind speed"], frameon=False, loc="upper left", ncol=2, fontsize=8.2)
        return self._save(fig, "monthly_energy_cf", "Monthly energy and mean wind speed chart")

    def chart_daily_specific_yield(self) -> dict:
        daily = self.analysis["performance"]["daily_specific_yield"]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.fill_between(daily.index, daily["specific_yield"], color="#DCE7F0", alpha=0.7, label="Daily specific yield")
        ax.plot(daily.index, daily["specific_yield"], color=self.tokens["primary_navy"], linewidth=0.8)
        ax.plot(daily.index, daily["rolling_30d"], color=self.tokens["danger_red"], linewidth=1.5, label="30-day rolling mean")
        ax.set_title("Daily Specific Yield And 30-day Rolling Mean", fontsize=11, fontweight="bold")
        ax.set_ylabel("Specific yield (kWh/kW/day)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        ax.legend(frameon=False, loc="upper left", fontsize=8.2)
        return self._save(fig, "daily_specific_yield", "Daily specific yield chart")

    def chart_fleet_comparison(self) -> dict:
        comp = self.analysis["fleet"]
        names = list(comp.index)
        x = comp["availability_pct"].to_numpy(dtype=float)
        y = comp["performance_index_pct"].to_numpy(dtype=float)
        colors = []
        for _, row in comp.iterrows():
            if row["performance_index_pct"] < 90 or row["availability_pct"] < 92:
                colors.append(self.tokens["danger_red"])
            elif row["performance_index_pct"] < 95 or row["availability_pct"] < 95:
                colors.append(self.tokens["warning_amber"])
            else:
                colors.append(self.tokens["secondary_slate_blue"])
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.scatter(x, y, s=58, color=colors, alpha=0.88)
        ax.axvline(95, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax.axhline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        for name, x_val, y_val in zip(names, x, y):
            ax.annotate(name, (x_val, y_val), xytext=(4, 4), textcoords="offset points", fontsize=8)
        ax.set_title("Fleet Turbine Comparison", fontsize=11, fontweight="bold")
        ax.set_xlabel("Availability (%)")
        ax.set_ylabel("Performance index (%)")
        self._apply_axes_style(ax)
        return self._save(fig, "fleet_comparison", "Fleet turbine comparison chart")

    def chart_availability_trend(self) -> dict:
        monthly = self.analysis["availability"]["site_monthly"]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.fill_between(monthly.index, monthly.values, np.minimum(monthly.values.min() - 3, 75), color="#DCE7F0", alpha=0.85)
        ax.plot(monthly.index, monthly.values, color=self.tokens["primary_navy"], linewidth=1.8, marker="o", markersize=4.5)
        ax.axhline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        ax.set_title("Monthly Site Availability", fontsize=11, fontweight="bold")
        ax.set_ylabel("Availability (%)")
        ax.set_ylim(min(75, float(monthly.min()) - 3), 101)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        return self._save(fig, "availability_trend", "Monthly site availability chart")

    def chart_waterfall(self) -> dict:
        wf = self.analysis["losses"]["waterfall"]
        labels = ["Potential", "Availability loss", "Performance loss", "Residual", "Actual"]
        values = [wf["potential_mwh"], wf["availability_loss_mwh"], wf["performance_loss_mwh"], wf["residual_mwh"], wf["actual_mwh"]]
        colors = [
            self.tokens["primary_navy"],
            self.tokens["warning_amber"],
            self.tokens["danger_red"],
            self.tokens["deep_indigo"],
            self.tokens["success_green"],
        ]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.bar(0, values[0], color=colors[0], edgecolor="white")
        running = values[0]
        for idx, value in enumerate(values[1:4], start=1):
            ax.bar(idx, -value, bottom=running, color=colors[idx], edgecolor="white")
            running -= value
        ax.bar(4, values[4], color=colors[4], edgecolor="white")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel("Energy (MWh)")
        ax.set_title("Losses And Recoverability Waterfall", fontsize=11, fontweight="bold")
        self._apply_axes_style(ax)
        return self._save(fig, "waterfall", "Wind loss waterfall chart")

    def chart_monthly_availability_loss(self) -> dict:
        monthly = self.analysis["losses"]["monthly_availability_loss_mwh"]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.bar(monthly.index, monthly.values, width=20, color=self.tokens["warning_amber"], edgecolor="white")
        ax.set_title("Monthly Availability Loss Breakdown", fontsize=11, fontweight="bold")
        ax.set_ylabel("Loss (MWh)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        return self._save(fig, "monthly_availability_loss", "Monthly availability loss chart")

    def chart_fleet_power_curve(self) -> dict:
        curve = self.analysis["power_curve"]
        fig, axes = plt.subplots(2, 1, figsize=(8.4, 10.6), constrained_layout=True)
        ax1, ax2 = axes
        ref = curve["reference_curve"]
        ref_counts = curve.get("reference_curve_counts")
        reliable_ref = ref.copy()
        if ref_counts is not None:
            reliable_ref = reliable_ref.where(ref_counts >= 12)
        ax1.plot(reliable_ref.index, reliable_ref.values, color=self.tokens["primary_navy"], linewidth=2.1, label="Reference envelope")
        max_reliable_wind = np.nanmax(reliable_ref.index.to_numpy(dtype=float)[np.isfinite(reliable_ref.to_numpy(dtype=float))]) if reliable_ref.notna().any() else 20.0
        for turbine, series in curve["binned_by_turbine"].items():
            counts = curve.get("binned_counts_by_turbine", {}).get(turbine)
            reliable = series.copy()
            if counts is not None:
                reliable = reliable.where(counts >= 6)
            reliable = reliable.where(~((reliable.index >= 18.0) & (reliable < self.config["rated_power_kw"] * 0.75)))
            ax1.plot(reliable.index, reliable.values, linewidth=1.15, alpha=0.9, label=turbine)
        ax1.set_title("Fleet Power Curve Envelope", fontsize=11, fontweight="bold")
        ax1.set_xlabel("Wind speed (m/s)")
        ax1.set_ylabel("Power (kW)")
        ax1.set_xlim(0, min(max_reliable_wind + 0.75, 24.0))
        ax1.set_ylim(0, self.config["rated_power_kw"] * 1.06)
        self._apply_axes_style(ax1)
        ax1.legend(frameon=False, ncol=3, fontsize=8.2, loc="upper left")
        ax1.text(
            0.99,
            0.03,
            "High-wind bins with too few records are hidden.",
            transform=ax1.transAxes,
            ha="right",
            va="bottom",
            fontsize=8.2,
            color=self.tokens["muted_text"],
        )

        deviation = self.analysis["fleet"]["performance_index_pct"].sort_values()
        colors = [
            self.tokens["danger_red"] if value < 90 else self.tokens["warning_amber"] if value < 95 else self.tokens["secondary_slate_blue"]
            for value in deviation.values
        ]
        ax2.barh(deviation.index, deviation.values, color=colors, edgecolor="white")
        ax2.axvline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        ax2.set_title("Performance Index By Turbine", fontsize=11, fontweight="bold")
        ax2.set_xlabel("Performance index (%)")
        x_min = max(0.0, float(np.floor(deviation.min() / 5.0) * 5.0) - 5.0)
        ax2.set_xlim(x_min, 102)
        for turbine, value in deviation.items():
            ax2.text(min(value + 0.5, 101.5), turbine, f"{value:.1f}%", va="center", fontsize=8.5, color=self.tokens["primary_navy"])
        self._apply_axes_style(ax2)
        ax2.grid(True, axis="x", color=self.tokens["border_grey"], alpha=0.45, linewidth=0.8)
        ax2.grid(False, axis="y")
        return self._save(fig, "fleet_power_curve", "Fleet power curve diagnostics")

    def chart_site_locator_map(self) -> dict | None:
        """France image map with highlighted wind-farm location."""
        import math

        location = self.config.get("site_location") or {}
        LON = location.get("longitude")
        LAT = location.get("latitude")
        if LON is None or LAT is None:
            return None

        # france.jpg lives in the sibling SCADA Analysis folder
        img_path = Path(__file__).parent.parent / "SCADA Analysis" / "france.jpg"
        img = plt.imread(str(img_path))

        # Geographic extent the image covers (lon_min, lon_max, lat_min, lat_max)
        extent = (-6.0, 10.2, 41.0, 51.6)

        mean_lat_rad = math.radians(47.0)
        asp = 1.0 / math.cos(mean_lat_rad)  # ~1.47

        fig, ax = plt.subplots(figsize=(7.5, 7.5))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.set_position([0.01, 0.01, 0.98, 0.98])

        ax.imshow(img, extent=extent, aspect="auto", origin="upper", zorder=1)

        # Site dot — prominent green (wind) with outer ring
        ax.scatter([LON], [LAT], s=280, color=self.tokens["success_green"],
                   linewidths=2, edgecolors="white", zorder=6)
        ax.scatter([LON], [LAT], s=560, facecolors="none",
                   edgecolors=self.tokens["success_green"], linewidths=1.2,
                   alpha=0.40, zorder=5)

        # Callout annotation — south-west of site into open France
        ax.annotate(
            f"LUCE II Wind Farm\n49°48′N  |  2°38′E",
            xy=(LON, LAT),
            xytext=(LON - 4.5, LAT - 3.5),
            fontsize=9, fontweight="bold",
            color=self.tokens["primary_navy"], zorder=7,
            ha="left",
            arrowprops=dict(
                arrowstyle="->", color=self.tokens["primary_navy"],
                lw=1.2, connectionstyle="arc3,rad=0.2",
            ),
            bbox=dict(
                boxstyle="round,pad=0.40", facecolor="white", alpha=0.93,
                edgecolor=self.tokens["primary_navy"], linewidth=0.9,
            ),
        )

        ax.set_aspect(asp, adjustable="datalim")
        ax.set_xlim(-5.8, 9.8)
        ax.set_ylim(41.2, 51.5)
        ax.axis("off")

        return self._save_png(fig, "site_locator_map", "France map with wind farm location")

    def chart_fault_duration_by_turbine(self) -> dict | None:
        fault_summary = self.analysis["messages"]["fault_family_summary"]
        if fault_summary.empty:
            return None
        top = fault_summary.head(6)
        pivot = top.pivot_table(index="fault_family", columns="turbine", values="duration_h", aggfunc="sum").fillna(0)
        pivot = pivot.reindex(sorted(pivot.columns, key=_sort_key), axis=1)
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        bottom = np.zeros(len(pivot.index))
        palette = [
            self.tokens["primary_navy"],
            self.tokens["secondary_slate_blue"],
            self.tokens["accent_orange"],
            self.tokens["deep_indigo"],
            self.tokens["warning_amber"],
        ]
        for idx, turbine in enumerate(pivot.columns):
            values = pivot[turbine].to_numpy(dtype=float)
            ax.barh(pivot.index, values, left=bottom, color=palette[idx % len(palette)], edgecolor="white", label=turbine)
            bottom += values
        ax.set_title("Top Fault Families By Downtime Contribution", fontsize=11, fontweight="bold")
        ax.set_xlabel("Downtime (h)")
        self._apply_axes_style(ax)
        ax.legend(frameon=False, ncol=4, fontsize=7.8, loc="lower right")
        return self._save(fig, "fault_duration_by_turbine", "Fault downtime by turbine chart")


def build_wind_report_assets(*, config: dict, analysis: dict, assets_dir: Path) -> dict:
    return WindChartFactory(config=config, analysis=analysis, assets_dir=assets_dir).build_all()


def _toc_page(pages: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for page in pages:
        if page.get("toc_hide") or not page.get("title") or page["template"] == "cover":
            continue
        group = page.get("toc_group", "Report")
        groups.setdefault(group, []).append({"title": page["title"]})
    return {
        "template": "toc",
        "title": "Table of Contents",
        "groups": [{"title": title, "entries": entries} for title, entries in groups.items()],
    }


def build_wind_report_data(*, config: dict, analysis: dict, charts: dict, outputs: dict) -> dict:
    generated_at = config.get("generated_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    cover_image = config.get("cover_image_path")
    report = {
        "document": {
            "report_title": config["report_title"],
            "site_name": config["site_name"],
            "generated_at": generated_at,
            "data_dir": str(config["data_dir"]),
            "output_dir": str(config["output_dir"]),
            "output_format": outputs["output_format"],
            "company": "8.2 Advisory | A Dolfines Company",
            "logo_white": Path(config["logo_white"]).as_uri(),
            "logo_color": Path(config["logo_color"]).as_uri(),
            "favicon": Path(config["favicon"]).as_uri(),
            "cover_image": Path(cover_image).as_uri() if cover_image and Path(cover_image).exists() else None,
            "debug_layout": config["style_tokens"]["debug_layout"],
            "tokens": config["style_tokens"],
        },
        "pages": [],
    }

    annualisation_note = f"Annualised from an observed {analysis['period_days']:.0f}-day SCADA period."
    site_location = config.get("site_location") or {}

    tech_rows = [
        {"Parameter": "Site name", "Value": config["site_name"], "Notes": "Wind farm performance assessment baseline."},
        {"Parameter": "Analysis period", "Value": f"{analysis['period_start']:%d %b %Y} to {analysis['period_end']:%d %b %Y}", "Notes": "Based on the available 5-minute operation export."},
        {"Parameter": "Fleet size", "Value": str(config["n_turbines"]), "Notes": "Turbines included in the fleet-wide assessment."},
        {"Parameter": "Rated turbine power", "Value": _fmt_num(config["rated_power_kw"], 0, " kW"), "Notes": "Derived from the observed operating envelope."},
        {"Parameter": "Installed capacity", "Value": _fmt_num(config["cap_ac_kw"] / 1000.0, 1, " MW"), "Notes": "Fleet total based on the observed turbine rating."},
        {"Parameter": "Sampling interval", "Value": _fmt_num(config["interval_minutes"], 0, " min"), "Notes": "Native SCADA export interval."},
        {"Parameter": "Primary channels", "Value": "Power, wind speed, wind direction, nacelle position, rotor speed, generator speed", "Notes": "Used for data-quality and performance screening."},
        {"Parameter": "Downtime evidence", "Value": "Manufacturer message logs and low-output detection", "Notes": "Used together to distinguish low-wind behaviour from operational downtime."},
        {"Parameter": "Performance reference", "Value": "Fleet-derived reference power curve envelope", "Notes": "Constructed from the upper operating envelope across valid wind-speed bins."},
        {"Parameter": "Loss valuation", "Value": f"EUR {config['tariff_eur_per_kwh']:.02f}/kWh", "Notes": "Applied to estimated recoverable energy losses in the action register."},
    ]
    tech_rows_a = tech_rows[:5]
    tech_rows_b = tech_rows[5:]

    dq = analysis["data_quality"]
    perf = analysis["performance"]
    fleet = analysis["fleet"]
    availability = analysis["availability"]
    losses = analysis["losses"]
    top_actions = analysis["punchlist"][:6]
    top_faults = analysis["messages"]["fault_family_summary"].head(6)
    top_exposed_turbine = fleet.sort_values(["recoverable_eur_year", "performance_index_pct"], ascending=[False, True]).index[0]

    overview_pages = [
        {
            "template": "cover",
            "title": config["report_title"],
            "subtitle": "SCADA Performance Analysis Report",
            "metadata": [
                ("Project", config["site_name"]),
                ("Asset", f"{config['cap_ac_kw'] / 1000.0:,.1f} MW wind farm"),
                ("Analysis period", f"{analysis['period_start']:%d %b %Y} to {analysis['period_end']:%d %b %Y}"),
                ("Technology", f"{config['n_turbines']} x {_fmt_num(config['rated_power_kw'] / 1000.0, 1, ' MW')} wind turbines"),
                ("Issued", generated_at),
            ],
        },
        {
            "template": "section",
            "id": "executive-summary",
            "toc_group": "Overview",
            "title": "Executive Summary",
            "kicker": "Highest-value findings",
            "summary": "Wind resource capture, fleet availability, and recoverable loss priorities.",
            "commentary_title": "Overall assessment",
            "commentary": [
                f"The fleet delivered {_fmt_num(perf['actual_energy_mwh'], 0, ' MWh')} over the analysed period, with a fleet performance index of {_fmt_pct(perf['fleet_performance_index_pct'])} against the derived reference power curve.",
                f"Fleet technical availability averaged {_fmt_pct(availability['site_availability_pct'])}. Estimated availability-led losses account for {_fmt_num(losses['availability_loss_mwh'], 0, ' MWh')}, while residual performance shortfall adds {_fmt_num(losses['performance_loss_mwh'], 0, ' MWh')}.",
                f"Annualised recoverable value is {_fmt_eur_per_year(losses['recoverable_loss_eur_year'])}. {annualisation_note}",
                f"Power completeness is {_fmt_pct(dq['overall_power_pct'])}, wind-speed completeness is {_fmt_pct(dq['overall_wind_pct'])}, and wind-direction completeness is {_fmt_pct(dq['overall_direction_pct'])}. The dataset is sufficiently complete for fleet-level diagnostics.",
            ],
            "kpis": [
                _kpi("Fleet performance index", _fmt_pct(perf["fleet_performance_index_pct"]), "Target >= 95%", "danger" if perf["fleet_performance_index_pct"] < 90 else "warning" if perf["fleet_performance_index_pct"] < 95 else "success"),
                _kpi("Fleet availability", _fmt_pct(availability["site_availability_pct"]), "Target >= 95%", "danger" if availability["site_availability_pct"] < 92 else "warning" if availability["site_availability_pct"] < 95 else "success"),
                _kpi("Recoverable loss", _fmt_eur_per_year(losses["recoverable_loss_eur_year"]), annualisation_note, "danger" if losses["recoverable_loss_eur_year"] >= 5000 else "warning"),
                _kpi("Recoverable energy", _fmt_num(losses["recoverable_loss_mwh_year"], 0, " MWh/yr"), annualisation_note, "warning"),
            ],
            "tables": [
                _table_block(
                    "Top Recommended Actions",
                    ["Priority", "Category", "Estimated loss", "Estimated loss (EUR/yr)", "Action"],
                    [
                        {
                            "Priority": item["priority"],
                            "Category": item["category"],
                            "Estimated loss": _fmt_num(item["mwh_loss_year"], 1, " MWh/yr"),
                            "Estimated loss (EUR/yr)": _fmt_eur_per_year(item["eur_loss_year"]),
                            "Action": item["action"],
                            "_row_class": "row-danger" if item["priority"] == "HIGH" else "row-warning",
                        }
                        for item in top_actions[:3]
                    ],
                )
            ],
            "findings": [
                {
                    "title": "Primary shortfall driver",
                    "severity": "warning" if losses["availability_loss_mwh"] >= losses["performance_loss_mwh"] else "danger",
                    "body": "Availability-led losses dominate the current shortfall, so maintenance response and recurring trip resolution are the first-value actions."
                    if losses["availability_loss_mwh"] >= losses["performance_loss_mwh"]
                    else "Turbines are frequently available but not converting wind resource efficiently, so power-curve underperformance is the leading issue.",
                },
                {
                    "title": "Most exposed turbine",
                    "severity": "danger",
                    "body": f"{top_exposed_turbine} carries the highest annualised recoverable value exposure in the current fleet ranking.",
                },
            ],
            "notes": [],
        },
        {
            "template": "section",
            "id": "performance-kpi-dashboard",
            "toc_group": "Overview",
            "title": "Performance KPI Dashboard",
            "kicker": "Consultancy dashboard",
            "summary": "Core fleet KPIs for the current wind-farm assessment.",
            "commentary_title": "KPI interpretation",
            "commentary": [
                f"The dashboard combines operational delivery, data confidence, and annualised value at stake. {annualisation_note}"
            ],
            "kpis": [
                _kpi("Power completeness", _fmt_pct(dq["overall_power_pct"]), "Target >= 98%", "success" if dq["overall_power_pct"] >= 98 else "warning"),
                _kpi("Fleet performance index", _fmt_pct(perf["fleet_performance_index_pct"]), "Target >= 95%", "danger" if perf["fleet_performance_index_pct"] < 90 else "warning" if perf["fleet_performance_index_pct"] < 95 else "success"),
                _kpi("Fleet availability", _fmt_pct(availability["site_availability_pct"]), "Target >= 95%", "danger" if availability["site_availability_pct"] < 92 else "warning" if availability["site_availability_pct"] < 95 else "success"),
                _kpi("Recoverable value", _fmt_eur_per_year(losses["recoverable_loss_eur_year"]), annualisation_note, "danger" if losses["recoverable_loss_eur_year"] >= 5000 else "warning"),
            ],
            "tables": [
                _table_block(
                    "Operational Performance",
                    ["KPI", "Value", "Reference", "Reading"],
                    [
                        {"KPI": "Power completeness", "Value": _fmt_pct(dq["overall_power_pct"]), "Reference": ">= 98%", "Reading": "SCADA coverage is adequate for fleet diagnostics.", "_row_class": "row-success" if dq["overall_power_pct"] >= 98 else "row-warning"},
                        {"KPI": "Wind-speed completeness", "Value": _fmt_pct(dq["overall_wind_pct"]), "Reference": ">= 98%", "Reading": "Wind-speed coverage supports power-curve benchmarking.", "_row_class": "row-success" if dq["overall_wind_pct"] >= 98 else "row-warning"},
                        {"KPI": "Fleet performance index", "Value": _fmt_pct(perf["fleet_performance_index_pct"]), "Reference": ">= 95%", "Reading": "Measured energy capture against the fleet reference envelope.", "_row_class": "row-danger" if perf["fleet_performance_index_pct"] < 90 else "row-warning" if perf["fleet_performance_index_pct"] < 95 else "row-success"},
                    ],
                ),
                _table_block(
                    "Value And Recoverability",
                    ["KPI", "Value", "Reference", "Reading"],
                    [
                        {"KPI": "Potential energy", "Value": _fmt_num(perf["potential_energy_mwh"], 0, " MWh"), "Reference": "Observed period", "Reading": "Upper-envelope production derived from fleet SCADA.", "_row_class": "row-info"},
                        {"KPI": "Fleet availability", "Value": _fmt_pct(availability["site_availability_pct"]), "Reference": ">= 95%", "Reading": "Share of wind-eligible intervals with expected turbine response.", "_row_class": "row-danger" if availability["site_availability_pct"] < 92 else "row-warning" if availability["site_availability_pct"] < 95 else "row-success"},
                        {"KPI": "Recoverable loss value", "Value": _fmt_eur_per_year(losses["recoverable_loss_eur_year"]), "Reference": annualisation_note, "Reading": "Annualised value of current availability and performance shortfall.", "_row_class": "row-danger" if losses["recoverable_loss_eur_year"] >= 5000 else "row-warning"},
                    ],
                )
            ],
            "figures": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "site-overview",
            "toc_group": "Overview",
            "title": "Site Overview And Technical Scope",
            "kicker": "Project baseline",
            "summary": "Wind-farm scope, asset definition, and engineering method.",
            "commentary_title": "Method and asset summary",
            "commentary": [
                f"{config['site_name']} comprises {config['n_turbines']} turbines with an observed rated output of approximately {_fmt_num(config['rated_power_kw'] / 1000.0, 1, ' MW')} per unit.",
                "This first-pass WINDPAT assessment uses fleet operation data and manufacturer messages to screen telemetry quality, estimate wind-resource capture, quantify availability-led losses, and prioritise corrective actions.",
                f"Geographic siting is shown from the supplied KMZ marker at {site_location['latitude']:.4f} N, {site_location['longitude']:.4f} E."
                if site_location.get("latitude") is not None and site_location.get("longitude") is not None
                else "No site KMZ marker was available, so the geographic locator panel is omitted.",
            ],
            "kpis": [
                _kpi("Installed capacity", _fmt_num(config["cap_ac_kw"] / 1000.0, 1, " MW")),
                _kpi("Turbines analysed", str(config["n_turbines"])),
                _kpi("Reporting interval", _fmt_num(config["interval_minutes"], 0, " min")),
                _kpi("Tariff assumption", f"EUR {config['tariff_eur_per_kwh']:.02f}/kWh"),
            ],
            "tables": [],
            "figures": [
                _figure_block(charts, "site_locator_map", "Wind Farm Geographic Location", "The location marker is extracted directly from the KMZ supplied with the assessment package.", width="full")
            ]
            if charts.get("site_locator_map")
            else [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "technical-parameters",
            "toc_group": "Overview",
            "title": "Technical Configuration & Analysis Parameters",
            "kicker": "Configuration basis",
            "summary": "Asset definition, SCADA basis, and diagnostic assumptions used for this report.",
            "commentary_title": "Configuration summary",
            "commentary": [
                "The table below consolidates the site configuration and the analysis assumptions used to translate raw 5-minute SCADA streams into fleet-level performance and loss indicators."
            ],
            "tables": [
                _table_block("Site And SCADA Basis", ["Parameter", "Value", "Notes"], tech_rows_a),
                _table_block("Diagnostic Assumptions", ["Parameter", "Value", "Notes"], tech_rows_b),
            ],
            "figures": [],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
    ]

    main_pages = [
        {
            "template": "section",
            "id": "data-quality",
            "toc_group": "Main Report",
            "paginate": False,
            "title": "Data Quality",
            "kicker": "Telemetry confidence",
            "summary": "Power, wind-speed, and wind-direction completeness reviewed before interpreting production losses.",
            "commentary_title": "Engineering interpretation",
            "commentary": [
                f"Power completeness averages {_fmt_pct(dq['overall_power_pct'])} across the fleet. The remaining gaps are concentrated in a limited number of turbines rather than a site-wide telemetry outage.",
                f"Wind-speed completeness is {_fmt_pct(dq['overall_wind_pct'])} and wind-direction completeness is {_fmt_pct(dq['overall_direction_pct'])}. That is sufficient for reference power-curve benchmarking and directional context.",
            ],
            "kpis": [
                _kpi("Power completeness", _fmt_pct(dq["overall_power_pct"]), "Target >= 98%", "success" if dq["overall_power_pct"] >= 98 else "warning"),
                _kpi("Wind speed completeness", _fmt_pct(dq["overall_wind_pct"]), "Target >= 98%", "success" if dq["overall_wind_pct"] >= 98 else "warning"),
                _kpi("Wind direction completeness", _fmt_pct(dq["overall_direction_pct"]), "Target >= 98%", "success" if dq["overall_direction_pct"] >= 98 else "warning"),
                _kpi("Valid operating records", _fmt_num(dq["valid_operating_records"], 0)),
            ],
            "figures": [_figure_block(charts, "data_availability_overview", "Per-Turbine Power Completeness", "The chart highlights turbines where missing power intervals could bias relative performance interpretation.", width="full")],
            "tables": [],
            "findings": [
                {
                    "title": "Data confidence",
                    "severity": "success" if dq["overall_power_pct"] >= 98 else "warning",
                    "body": "The available telemetry is strong enough for fleet comparison and loss quantification without material data-confidence caveats."
                    if dq["overall_power_pct"] >= 98
                    else "Data gaps remain manageable, but turbine-to-turbine comparisons should still be read with care where completeness is visibly lower.",
                }
            ],
            "notes": [],
        },
        {
            "template": "section",
            "id": "data-quality-detail",
            "toc_group": "Main Report",
            "title": "Data Quality Detail",
            "kicker": "Monthly completeness",
            "summary": "Monthly visibility of turbine-level data gaps.",
            "commentary_title": "Monthly interpretation",
            "commentary": [
                "The monthly heat map is useful for separating persistent channel issues from one-off telemetry outages. Concentrated low-completeness months should be checked before using month-specific performance conclusions for contractual purposes."
            ],
            "figures": [_figure_block(charts, "data_availability_heatmap", "Monthly Turbine Power Completeness Heat Map", "Recurring low-completeness months are visible by turbine and help distinguish persistent telemetry issues from isolated gaps.", width="full")],
            "tables": [],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "performance-overview",
            "toc_group": "Main Report",
            "title": "Performance Overview",
            "kicker": "Wind-resource capture",
            "summary": "Monthly production and fleet-normalised energy capture.",
            "commentary_title": "Performance interpretation",
            "commentary": [
                f"The fleet performance index of {_fmt_pct(perf['fleet_performance_index_pct'])} indicates how much of the derived reference energy envelope was captured. Comparing monthly energy with mean wind speed makes it easier to separate true technical underperformance from simple wind-resource seasonality."
            ],
            "figures": [
                _figure_block(charts, "monthly_energy_cf", "Monthly Energy And Mean Wind Speed", "Monthly energy bars are overlaid with mean wind speed so lower production can be compared directly against the wind regime.", width="full"),
                _figure_block(charts, "daily_specific_yield", "Daily Specific Yield And 30-day Rolling Mean", "The rolling mean shows whether production weakness is persistent rather than driven by isolated trip days.", width="full"),
            ],
            "tables": [],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "fleet-comparison",
            "toc_group": "Main Report",
            "title": "Fleet Turbine Comparison",
            "kicker": "Relative ranking",
            "summary": "Availability and performance-index comparison across the four turbines.",
            "commentary_title": "Fleet interpretation",
            "commentary": [
                "The scatter separates turbines that are mainly downtime-driven from those that remain available but convert the wind resource less efficiently than the fleet envelope would suggest."
            ],
            "figures": [_figure_block(charts, "fleet_comparison", "Performance Index Versus Availability", "Lower-left points warrant immediate intervention because both uptime and energy capture are weak.", width="full")],
            "tables": [
                _table_block(
                    "Lowest Performing Turbines",
                    ["Turbine", "Availability", "Performance index", "Recoverable loss", "Estimated loss (EUR/yr)"],
                    [
                        {
                            "Turbine": turbine,
                            "Availability": _fmt_pct(row["availability_pct"]),
                            "Performance index": _fmt_pct(row["performance_index_pct"]),
                            "Recoverable loss": _fmt_num(row["recoverable_mwh_year"], 1, " MWh/yr"),
                            "Estimated loss (EUR/yr)": _fmt_eur_per_year(row["recoverable_eur_year"]),
                            "_row_class": "row-danger" if row["recoverable_eur_year"] >= 5000 else "row-warning",
                        }
                        for turbine, row in fleet.sort_values(["recoverable_eur_year", "performance_index_pct"], ascending=[False, True]).head(4).iterrows()
                    ],
                )
            ],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "availability-reliability",
            "toc_group": "Main Report",
            "title": "Availability And Reliability",
            "kicker": "Operational continuity",
            "summary": "Monthly availability and dominant downtime drivers from the message logs.",
            "commentary_title": "Reliability interpretation",
            "commentary": [
                f"Site availability averaged {_fmt_pct(availability['site_availability_pct'])}. Recurring manufacturer-status messages were screened to separate genuine technical stoppages from low-wind idle conditions.",
                "Persistent recurrence of the same fault family across several turbines usually indicates either a common subsystem weakness or a fleet-wide maintenance practice issue rather than an isolated unit event.",
            ],
            "figures": [_figure_block(charts, "availability_trend", "Monthly Site Availability", "Availability is computed only for wind-eligible intervals, so the metric reflects technical uptime rather than the underlying wind regime.", width="full")],
            "tables": [
                _table_block(
                    "Lowest Availability / Highest Downtime Units",
                    ["Turbine", "Availability", "Downtime", "Top fault family"],
                    [
                        {
                            "Turbine": turbine,
                            "Availability": _fmt_pct(row["availability_pct"]),
                            "Downtime": _fmt_num(row["downtime_h"], 1, " h"),
                            "Top fault family": row["top_fault_family"] or "No dominant technical family",
                        }
                        for turbine, row in fleet.sort_values(["availability_pct", "downtime_h"]).head(4).iterrows()
                    ],
                )
            ],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "losses",
            "toc_group": "Main Report",
            "title": "Losses And Recoverability",
            "kicker": "Value at stake",
            "summary": "Potential energy, availability loss, performance loss, and recoverable value.",
            "commentary_title": "Loss interpretation",
            "commentary": [
                f"Recoverable losses total {_fmt_num(losses['recoverable_loss_mwh'], 0, ' MWh')} over the analysed period, equivalent to {_fmt_eur_per_year(losses['recoverable_loss_eur_year'])}.",
                "Availability loss quantifies periods where the wind resource was present but one or more turbines were effectively unavailable. Performance loss captures sub-envelope operation after excluding those clear downtime periods.",
            ],
            "figures": [
                _figure_block(charts, "waterfall", "Losses And Recoverability Waterfall", "The waterfall starts from fleet potential energy and shows how availability and performance losses reduce realised production.", width="full"),
                _figure_block(charts, "monthly_availability_loss", "Monthly Availability Loss Breakdown", "This chart highlights which months contributed most to the total availability deficit.", width="full"),
            ],
            "tables": [
                _table_block(
                    "Loss Summary",
                    ["Metric", "Value"],
                    [
                        {"Metric": "Potential energy", "Value": _fmt_num(losses["potential_mwh"], 0, " MWh")},
                        {"Metric": "Actual energy", "Value": _fmt_num(losses["actual_mwh"], 0, " MWh")},
                        {"Metric": "Availability loss", "Value": _fmt_num(losses["availability_loss_mwh"], 0, " MWh")},
                        {"Metric": "Performance loss", "Value": _fmt_num(losses["performance_loss_mwh"], 0, " MWh")},
                        {"Metric": "Recoverable energy (annualised)", "Value": _fmt_num(losses["recoverable_loss_mwh_year"], 0, " MWh/yr")},
                        {"Metric": "Recoverable value (annualised)", "Value": _fmt_eur_per_year(losses["recoverable_loss_eur_year"])},
                    ],
                )
            ],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "section",
            "id": "action-punchlist",
            "toc_group": "Main Report",
            "title": "Full Action Punchlist",
            "kicker": "Corrective priorities",
            "summary": "Client-facing action register ordered by current revenue exposure.",
            "commentary_title": "Action interpretation",
            "commentary": [
                f"The punchlist ranks actions by annualised recoverable revenue. {annualisation_note}"
            ],
            "tables": [
                _table_block(
                    "Full Action Punchlist",
                    ["Priority", "Category", "Issue", "Recommended action", "Estimated loss", "Estimated loss (EUR/yr)"],
                    [
                        {
                            "Priority": item["priority"],
                            "Category": item["category"],
                            "Issue": item["issue"],
                            "Recommended action": item["action"],
                            "Estimated loss": _fmt_num(item["mwh_loss_year"], 1, " MWh/yr"),
                            "Estimated loss (EUR/yr)": _fmt_eur_per_year(item["eur_loss_year"]),
                            "_row_class": "row-danger" if item["priority"] == "HIGH" else "row-warning",
                        }
                        for item in analysis["punchlist"]
                    ],
                )
            ],
            "figures": [],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "appendix",
            "id": "appendix-power-curve",
            "toc_group": "Appendix",
            "title": "Appendix - Fleet Power Curve Diagnostics",
            "summary": "Reference-envelope construction and turbine-level power-curve positioning.",
            "commentary": [],
            "figures": [_figure_block(charts, "fleet_power_curve", "Fleet Power Curve Diagnostics", "Reference and turbine-level binned power curves are shown together with the resulting performance-index ranking.", width="full")],
            "tables": [],
            "findings": [],
            "notes": [],
        },
        {
            "template": "appendix",
            "id": "appendix-faults",
            "toc_group": "Appendix",
            "paginate": False,
            "title": "Appendix - Fault Message Summary",
            "summary": "Dominant fault families and downtime contribution by turbine.",
            "commentary": [
                "Low-wind and normal-status messages were excluded from the ranked downtime families so the appendix remains focused on actionable operational issues."
            ],
            "figures": [_figure_block(charts, "fault_duration_by_turbine", "Top Fault Families By Downtime Contribution", "Downtime hours are grouped by fault family and turbine to highlight common-mode issues.", width="full")] if charts.get("fault_duration_by_turbine") else [],
            "tables": [
                _table_block(
                    "Top Fault Families",
                    ["Fault family", "Turbine", "Count", "Downtime", "Operational implication"],
                    [
                        {
                            "Fault family": row["fault_family"],
                            "Turbine": row["turbine"],
                            "Count": _fmt_num(row["count"], 0),
                            "Downtime": _fmt_num(row["duration_h"], 1, " h"),
                            "Operational implication": row["operational_implication"],
                        }
                        for _, row in top_faults.iterrows()
                    ],
                    appendix_only=True,
                )
            ],
            "findings": [],
            "notes": [],
        },
    ]

    all_pages = [overview_pages[0], *overview_pages[1:], *main_pages]
    try:
        from report.build_report_data import _paginate_section_like_page
    except ImportError:
        paginated_pages = all_pages[1:]
    else:
        paginated_pages: list[dict] = []
        for page in all_pages[1:]:
            paginated_pages.extend(_paginate_section_like_page(page))
    report["pages"] = [all_pages[0], _toc_page(paginated_pages), *paginated_pages]
    return report
