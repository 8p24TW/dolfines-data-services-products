from __future__ import annotations

from datetime import datetime
from math import asin, ceil, cos, radians, sin, sqrt
from pathlib import Path
import re
import sys

import matplotlib.dates as mdates
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

# Turbine knowledge base — graceful fallback if file missing
try:
    _kb_dir = str(Path(__file__).parent)
    if _kb_dir not in sys.path:
        sys.path.insert(0, _kb_dir)
    from turbine_knowledge_base import TURBINE_DB, lookup, best_match as _kb_best_match  # type: ignore
    _KB_AVAILABLE = True
except ImportError:
    _KB_AVAILABLE = False
    TURBINE_DB: dict = {}  # type: ignore
    def lookup(*a, **k): return None  # type: ignore[misc]
    def _kb_best_match(*a, **k): return None  # type: ignore[misc]


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
    return f"€{value:,.0f}"


def _fmt_eur_per_year(value: float | int | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"€{value:,.0f}/yr"


def _fmt_keur_per_year(value: float | int | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"€{value / 1000:.1f}k/yr"


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
            self.chart_turbine_layout_map,
            self.chart_data_availability_overview,
            self.chart_data_availability_heatmap,
            self.chart_monthly_energy_cf,
            self.chart_daily_specific_yield,
            self.chart_fleet_comparison,
            self.chart_availability_trend,
            self.chart_waterfall,
            self.chart_monthly_availability_loss,
            self.chart_performance_index,
            self.chart_fault_duration_by_turbine,
        ]:
            result = builder()
            if result:
                charts[result["id"]] = result
        for chart in self._turbine_scatter_charts():
            charts[chart["id"]] = chart
        wind_rose_chart = self.chart_wind_roses_all_turbines()
        if wind_rose_chart:
            charts[wind_rose_chart["id"]] = wind_rose_chart
        avail_heatmap = self.chart_monthly_availability_heatmap()
        if avail_heatmap:
            charts[avail_heatmap["id"]] = avail_heatmap
        for chart in self._rpm_vs_power_charts():
            charts[chart["id"]] = chart
        for chart in self._pitch_vs_power_charts():
            charts[chart["id"]] = chart
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
        # Explicit ticks only at actual data months — prevents any out-of-range month tick
        ax1.set_xticks(monthly.index)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax1.set_xlim(monthly.index[0] - pd.Timedelta(days=15), monthly.index[-1] + pd.Timedelta(days=15))
        self._apply_axes_style(ax1)
        plt.setp(ax1.get_xticklabels(), rotation=90, ha="center", va="top", fontsize=7.5)
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
        ax.set_xlim(daily.index[0] - pd.Timedelta(days=3), daily.index[-1] + pd.Timedelta(days=3))
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
        fig, ax = plt.subplots(figsize=(9.5, 4.5), constrained_layout=True)
        fig.patch.set_facecolor("white")
        ax.fill_between(monthly.index, monthly.values, np.minimum(monthly.values.min() - 3, 75), color="#DCE7F0", alpha=0.85)
        ax.plot(monthly.index, monthly.values, color=self.tokens["primary_navy"], linewidth=1.8, marker="o", markersize=4.5)
        ax.axhline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        ax.set_title("Monthly Site Availability", fontsize=11, fontweight="bold")
        ax.set_ylabel("Availability (%)")
        ax.set_ylim(min(75, float(monthly.min()) - 3), 101)
        ax.set_xticks(monthly.index)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.set_xlim(monthly.index[0] - pd.Timedelta(days=15), monthly.index[-1] + pd.Timedelta(days=15))
        self._apply_axes_style(ax)
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", va="top", fontsize=9.5)
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
        ax.set_xticks(monthly.index)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.set_xlim(monthly.index[0] - pd.Timedelta(days=15), monthly.index[-1] + pd.Timedelta(days=15))
        self._apply_axes_style(ax)
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", va="top", fontsize=7.5)
        return self._save(fig, "monthly_availability_loss", "Monthly availability loss chart")

    def chart_performance_index(self) -> dict:
        """Standalone performance-index bar chart (separate page)."""
        deviation = self.analysis["fleet"]["performance_index_pct"].sort_values()
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        colors = [
            self.tokens["danger_red"] if v < 90 else self.tokens["warning_amber"] if v < 95 else self.tokens["secondary_slate_blue"]
            for v in deviation.values
        ]
        ax.barh(deviation.index, deviation.values, color=colors, edgecolor="white")
        ax.axvline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        ax.set_title("Performance Index By Turbine", fontsize=11, fontweight="bold")
        ax.set_xlabel("Performance index (%)")
        x_min = max(0.0, float(np.floor(deviation.min() / 5.0) * 5.0) - 5.0)
        ax.set_xlim(x_min, 102)
        for turbine, value in deviation.items():
            ax.text(min(value + 0.5, 101.5), turbine, f"{value:.1f}%", va="center", fontsize=8.5, color=self.tokens["primary_navy"])
        self._apply_axes_style(ax)
        ax.grid(True, axis="x", color=self.tokens["border_grey"], alpha=0.45, linewidth=0.8)
        ax.grid(False, axis="y")
        return self._save(fig, "performance_index", "Performance index by turbine")

    def _turbine_scatter_charts(self) -> list[dict]:
        """Four scatter plots per page (2×2), one per turbine."""
        curve = self.analysis["power_curve"]
        scatter_by_turbine = curve.get("scatter_by_turbine", {})
        rated = self.config["rated_power_kw"]
        turbines = sorted(scatter_by_turbine.keys(), key=_sort_key)

        # Build reliable reference curve — drop bins with < 12 observations
        ref = curve["reference_curve"]
        ref_counts = curve.get("reference_curve_counts")
        reliable_ref = ref.copy()
        if ref_counts is not None:
            reliable_ref = reliable_ref.where(ref_counts >= 12)
        reliable_ref = reliable_ref.dropna()
        ref_x = reliable_ref.index.to_numpy(dtype=float)
        ref_y = reliable_ref.to_numpy(dtype=float)
        max_wind = float(ref_x.max()) + 0.5 if len(ref_x) > 0 else 20.5

        charts = []
        groups = [turbines[i:i + 4] for i in range(0, len(turbines), 4)]
        for page_idx, group in enumerate(groups):
            fig, axes = plt.subplots(2, 2, figsize=(9.5, 9.2), squeeze=False)
            fig.patch.set_facecolor("white")

            for idx in range(4):
                row, col = divmod(idx, 2)
                ax = axes[row][col]
                if idx >= len(group):
                    ax.set_visible(False)
                    continue
                turbine = group[idx]
                scatter_df = scatter_by_turbine.get(turbine)
                if scatter_df is not None and not scatter_df.empty:
                    wind = scatter_df["wind_ms"].to_numpy(dtype=float)
                    power = scatter_df["power_kw"].to_numpy(dtype=float)
                    expected = np.interp(wind, ref_x, ref_y, left=0.0, right=rated)
                    curtailed = (wind >= 6.0) & (power < expected * 0.75) & (expected >= rated * 0.30)
                    ax.scatter(
                        wind[~curtailed], power[~curtailed],
                        s=3, color=self.tokens["secondary_slate_blue"],
                        alpha=0.22, linewidths=0, zorder=2, rasterized=True,
                    )
                    if curtailed.any():
                        ax.scatter(
                            wind[curtailed], power[curtailed],
                            s=5, color=self.tokens["accent_orange"],
                            alpha=0.55, linewidths=0, zorder=3, rasterized=True,
                            label="Potential curtailment",
                        )
                # Reliable reference curve (no high-wind artefacts)
                ax.plot(ref_x, ref_y, color=self.tokens["primary_navy"],
                        linewidth=2.0, zorder=5, label="Reference curve")
                ax.set_title(turbine, fontsize=10, fontweight="bold", color=self.tokens["primary_navy"])
                ax.set_xlabel("Wind speed (m/s)", fontsize=8.5)
                ax.set_ylabel("Power (kW)", fontsize=8.5)
                ax.set_xlim(0, max_wind)
                ax.set_ylim(-rated * 0.02, rated * 1.08)
                self._apply_axes_style(ax)
                ax.legend(frameon=False, fontsize=7.0, loc="upper left")

            fig.tight_layout(pad=1.5)
            chart_id = f"power_curve_scatter_p{page_idx + 1}"
            charts.append(self._save_png(fig, chart_id, f"Turbine scatter power curves — page {page_idx + 1}"))

        return charts

    def chart_turbine_layout_map(self) -> dict | None:
        """Zoom map of individual turbine positions using OSM satellite tiles."""
        try:
            import contextily as ctx
        except ImportError:
            return None

        import math

        # ── Turbine GPS coords (decimal degrees, WGS84) ──────────────────────
        TURBINES = {
            "LU09": (2 + 37/60 + 5.6/3600,  49 + 48/60 + 47.3/3600),
            "LU10": (2 + 36/60 + 45.6/3600, 49 + 48/60 + 6.9/3600),
            "LU11": (2 + 36/60 + 34.4/3600, 49 + 48/60 + 19.5/3600),
            "LU12": (2 + 36/60 + 15.1/3600, 49 + 48/60 + 32.0/3600),
        }
        SUBSTATION = (2 + 36/60 + 59.2/3600, 49 + 48/60 + 54.8/3600)

        # ── WGS84 → Web Mercator (EPSG:3857) without pyproj ──────────────────
        def _to_mercator(lon: float, lat: float) -> tuple[float, float]:
            R = 6378137.0
            x = math.radians(lon) * R
            y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
            return x, y

        t_xy = {name: _to_mercator(*lonlat) for name, lonlat in TURBINES.items()}
        sub_xy = _to_mercator(*SUBSTATION)

        all_x = [xy[0] for xy in t_xy.values()] + [sub_xy[0]]
        all_y = [xy[1] for xy in t_xy.values()] + [sub_xy[1]]
        pad = max((max(all_x) - min(all_x)) * 0.5, 600)

        fig, ax = plt.subplots(figsize=(7.5, 7.5))
        fig.patch.set_facecolor("white")

        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

        # Basemap — Esri WorldImagery (satellite)
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, zoom=15)
        except Exception:
            try:
                ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=15)
            except Exception:
                pass

        # Turbines
        for name, (x, y) in t_xy.items():
            ax.scatter(x, y, s=220, color=self.tokens["success_green"],
                       edgecolors="white", linewidths=1.5, zorder=6)
            ax.annotate(
                name,
                xy=(x, y), xytext=(8, 8), textcoords="offset points",
                fontsize=8.5, fontweight="bold", color="white", zorder=7,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=self.tokens["success_green"],
                          alpha=0.85, edgecolor="none"),
            )

        # GPS coordinate labels (small, below marker)
        coord_rows = {
            "LU09": "E 2°37′05.6″  N 49°48′47.3″",
            "LU10": "E 2°36′45.6″  N 49°48′06.9″",
            "LU11": "E 2°36′34.4″  N 49°48′19.5″",
            "LU12": "E 2°36′15.1″  N 49°48′32.0″",
        }
        for name, (x, y) in t_xy.items():
            ax.annotate(
                coord_rows[name],
                xy=(x, y), xytext=(8, -16), textcoords="offset points",
                fontsize=6.5, color="white", zorder=7,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#00000066", edgecolor="none"),
            )

        # Substation
        ax.scatter(*sub_xy, s=220, marker="D", color=self.tokens["warning_amber"],
                   edgecolors="white", linewidths=1.5, zorder=6)
        ax.annotate(
            "Poste de livraison",
            xy=sub_xy, xytext=(8, 8), textcoords="offset points",
            fontsize=8.5, fontweight="bold", color="white", zorder=7,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=self.tokens["warning_amber"],
                      alpha=0.85, edgecolor="none"),
        )
        ax.annotate(
            "E 2°36′59.2″  N 49°48′54.8″",
            xy=sub_xy, xytext=(8, -16), textcoords="offset points",
            fontsize=6.5, color="white", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#00000066", edgecolor="none"),
        )

        # Legend
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch
        legend_elements = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=self.tokens["success_green"], markersize=10,
                   label="Wind turbine"),
            Line2D([0], [0], marker="D", color="w",
                   markerfacecolor=self.tokens["warning_amber"], markersize=9,
                   label="Poste de livraison"),
        ]
        leg = ax.legend(handles=legend_elements, loc="lower right",
                        frameon=True, fontsize=8.5, framealpha=0.9,
                        edgecolor=self.tokens["primary_navy"])

        ax.set_axis_off()
        ax.set_title("LUCE II — Turbine Layout", fontsize=10, fontweight="bold",
                     color=self.tokens["primary_navy"], pad=4)

        return self._save_png(fig, "turbine_layout_map", "Turbine layout and GPS coordinates")

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

        from matplotlib.lines import Line2D

        fig, ax = plt.subplots(figsize=(9.5, 7.5))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        # Keep map axes same physical width as original (7.35 in); extra fig width holds legend
        ax.set_position([0.01, 0.01, 0.773, 0.98])

        ax.imshow(img, extent=extent, aspect="auto", origin="upper", zorder=1)

        # Site dot — prominent green (wind) with outer ring
        ax.scatter([LON], [LAT], s=280, color=self.tokens["success_green"],
                   linewidths=2, edgecolors="white", zorder=6)
        ax.scatter([LON], [LAT], s=560, facecolors="none",
                   edgecolors=self.tokens["success_green"], linewidths=1.2,
                   alpha=0.40, zorder=5)

        ax.set_aspect(asp, adjustable="datalim")
        ax.set_xlim(-5.8, 9.8)
        ax.set_ylim(41.2, 51.5)
        ax.axis("off")

        # Legend to the right of the map
        legend_elements = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=self.tokens["success_green"],
                   markeredgecolor="white", markersize=11,
                   label=f"LUCE II Wind Farm\n49°48′N  |  2°38′E")
        ]
        leg = ax.legend(
            handles=legend_elements,
            loc="upper left",
            bbox_to_anchor=(1.03, 1.0),
            frameon=True,
            fontsize=9,
            title="Site Location",
            title_fontsize=9.5,
            framealpha=0.95,
            edgecolor=self.tokens["primary_navy"],
        )
        leg.get_title().set_fontweight("bold")
        leg.get_title().set_color(self.tokens["primary_navy"])

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

    def chart_wind_roses_all_turbines(self) -> dict | None:
        wind_rose_data = self.analysis.get("wind_rose_data", {})
        if not wind_rose_data:
            return None
        turbines = sorted(wind_rose_data.keys(), key=_sort_key)
        n = len(turbines)
        ncols = min(n, 2)
        nrows = ceil(n / ncols)
        fig = plt.figure(figsize=(ncols * 5.75, nrows * 5.25 + 0.9), constrained_layout=True)
        fig.patch.set_facecolor("white")
        speed_bins = [0, 3, 6, 9, 12, 50]
        speed_labels = ["0-3", "3-6", "6-9", "9-12", ">12 m/s"]
        colors = ["#c6dbef", "#6baed6", "#2171b5", "#08519c", "#08306b"]
        dir_bin_centers = np.radians(np.arange(0, 360, 30))
        dir_labels = ["N", "NNE", "ENE", "E", "ESE", "SSE", "S", "SSW", "WSW", "W", "WNW", "NNW"]

        ax = None
        for idx, turbine in enumerate(turbines):
            ax = fig.add_subplot(nrows, ncols, idx + 1, projection="polar")
            ax.set_facecolor("white")
            ax.set_theta_direction(-1)
            ax.set_theta_zero_location("N")
            data = wind_rose_data[turbine]
            wd = data["wind_dir_deg"].values
            ws = data["wind_ms"].values
            total = len(wd)
            bottom_vals = np.zeros(12)
            for speed_lo, speed_hi, color, label in zip(speed_bins[:-1], speed_bins[1:], colors, speed_labels):
                mask_s = (ws >= speed_lo) & (ws < speed_hi)
                freq = []
                for i in range(12):
                    lo = (i * 30 - 15) % 360
                    hi = (i * 30 + 15) % 360
                    if lo < hi:
                        mask_d = (wd >= lo) & (wd < hi)
                    else:
                        mask_d = (wd >= lo) | (wd < hi)
                    freq.append(np.sum(mask_s & mask_d) / total * 100.0 if total > 0 else 0.0)
                freq = np.array(freq)
                ax.bar(dir_bin_centers, freq, width=np.radians(30), bottom=bottom_vals,
                       color=color, alpha=0.85, label=label, linewidth=0.3, edgecolor="white")
                bottom_vals += freq
            ax.set_xticks(dir_bin_centers)
            ax.set_xticklabels(dir_labels, fontsize=6.5, color=self.tokens["body_text"])
            ax.yaxis.set_visible(False)
            ax.spines["polar"].set_color(self.tokens["border_grey"])
            ax.set_title(turbine, fontsize=8.5, fontweight="bold", color=self.tokens["primary_navy"], pad=6)

        if ax is not None:
            handles, labels = ax.get_legend_handles_labels()
            fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=7,
                       frameon=False, title="Wind speed (m/s)", title_fontsize=7.5,
                       bbox_to_anchor=(0.5, -0.02))
        return self._save(fig, "wind_roses_all_turbines", "Wind rose by turbine")

    def chart_monthly_availability_heatmap(self) -> dict | None:
        turbine_monthly_avail = self.analysis.get("availability_monthly_by_turbine", {})
        if not turbine_monthly_avail:
            return None
        from matplotlib.colors import LinearSegmentedColormap
        turbines = sorted(turbine_monthly_avail.keys(), key=_sort_key)
        # Build sorted month list
        all_months = sorted({
            ts.strftime("%Y-%m")
            for series in turbine_monthly_avail.values()
            for ts in series.index
        })
        if not all_months:
            return None
        # Build matrix: rows=turbines, cols=months
        matrix = np.full((len(turbines), len(all_months)), np.nan)
        for r, t in enumerate(turbines):
            series = turbine_monthly_avail[t]
            for c, m in enumerate(all_months):
                matches = [float(series.iloc[i]) for i, ts in enumerate(series.index)
                           if ts.strftime("%Y-%m") == m]
                if matches and np.isfinite(matches[0]):
                    matrix[r, c] = matches[0]
        n_months = len(all_months)
        n_turbines = len(turbines)
        fig_w = max(7.0, min(n_months * 0.55 + 1.2, 13.0))
        fig_h = max(2.0, n_turbines * 0.65 + 1.0)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), constrained_layout=True)
        fig.patch.set_facecolor("white")
        cmap = LinearSegmentedColormap.from_list(
            "avail",
            [self.tokens["danger_red"], self.tokens["warning_amber"],
             "#FFFDE7", self.tokens["success_green"]],
            N=256,
        )
        masked = np.ma.masked_invalid(matrix)
        im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=80, vmax=100,
                       interpolation="nearest")
        ax.set_yticks(range(n_turbines))
        ax.set_yticklabels(turbines, fontsize=8.5, color=self.tokens["body_text"])
        month_labels = [m[5:] + "\n" + m[:4] for m in all_months]  # "MM\nYYYY"
        ax.set_xticks(range(n_months))
        ax.set_xticklabels(month_labels, fontsize=7, color=self.tokens["body_text"])
        ax.tick_params(length=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        # Draw thin grid lines between cells
        for x in np.arange(-0.5, n_months, 1):
            ax.axvline(x, color="white", linewidth=0.8)
        for y in np.arange(-0.5, n_turbines, 1):
            ax.axhline(y, color="white", linewidth=0.8)
        # Colour bar
        cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="Availability (%)")
        cb.ax.tick_params(labelsize=7)
        ax.set_title("Monthly Technical Availability By Turbine", fontsize=10,
                     fontweight="bold", color=self.tokens["primary_navy"], pad=6)
        return self._save(fig, "monthly_availability_heatmap",
                          "Monthly availability heatmap per turbine")

    def _rpm_vs_power_charts(self) -> list[dict]:
        rpm_data = self.analysis.get("rpm_scatter_data", {})
        if not rpm_data:
            return []
        turbines = sorted(rpm_data.keys(), key=_sort_key)
        results = []
        page_size = 4
        for page_idx in range(ceil(len(turbines) / page_size)):
            page_turbines = turbines[page_idx * page_size: (page_idx + 1) * page_size]
            n = len(page_turbines)
            ncols = min(n, 2)
            nrows = ceil(n / ncols)
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                                      figsize=(ncols * 4.5, nrows * 3.5),
                                      constrained_layout=True)
            fig.patch.set_facecolor("white")
            if n == 1:
                axes = np.array([[axes]])
            elif nrows == 1:
                axes = axes.reshape(1, -1)
            elif ncols == 1:
                axes = axes.reshape(-1, 1)
            rated_power = self.config.get("rated_power_kw", 3900.0)
            for i, turbine in enumerate(page_turbines):
                ax = axes[i // ncols, i % ncols]
                data = rpm_data[turbine]
                rpm_vals = data["rotor_rpm"].values
                pwr_vals = data["power_kw"].values
                pwr_frac = np.clip(pwr_vals / rated_power, 0, 1)
                ax.scatter(rpm_vals, pwr_vals, c=pwr_frac, cmap="Blues", s=3, alpha=0.5,
                            vmin=0, vmax=1)
                ax.set_title(turbine, fontsize=9, fontweight="bold", color=self.tokens["primary_navy"])
                ax.set_xlabel("Rotor speed (RPM)", fontsize=8)
                ax.set_ylabel("Power (kW)", fontsize=8)
                ax.set_ylim(bottom=-50)
                self._apply_axes_style(ax)
            for i in range(len(page_turbines), nrows * ncols):
                axes[i // ncols, i % ncols].set_visible(False)
            chart_id = f"rpm_vs_power_p{page_idx + 1}"
            results.append(self._save(fig, chart_id, f"Rotor RPM vs power scatter page {page_idx + 1}"))
        return results


    def _pitch_vs_power_charts(self) -> list[dict]:
        pitch_data = self.analysis.get("pitch_scatter_data", {})
        if not pitch_data:
            return []
        turbines = sorted(pitch_data.keys(), key=_sort_key)
        results = []
        page_size = 4
        rated_power = self.config.get("rated_power_kw", 3900.0)
        for page_idx in range(ceil(len(turbines) / page_size)):
            page_turbines = turbines[page_idx * page_size: (page_idx + 1) * page_size]
            n = len(page_turbines)
            ncols = min(n, 2)
            nrows = ceil(n / ncols)
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                                      figsize=(ncols * 4.5, nrows * 3.5),
                                      constrained_layout=True)
            fig.patch.set_facecolor("white")
            if n == 1:
                axes = np.array([[axes]])
            elif nrows == 1:
                axes = axes.reshape(1, -1)
            elif ncols == 1:
                axes = axes.reshape(-1, 1)
            for i, turbine in enumerate(page_turbines):
                ax = axes[i // ncols, i % ncols]
                data = pitch_data[turbine]
                pitch_vals = data["pitch_angle_deg"].values
                pwr_vals = data["power_kw"].values
                pwr_frac = np.clip(pwr_vals / rated_power, 0, 1)
                ax.scatter(pitch_vals, pwr_vals, c=pwr_frac, cmap="Blues", s=3, alpha=0.5,
                           vmin=0, vmax=1)
                ax.set_title(turbine, fontsize=9, fontweight="bold", color=self.tokens["primary_navy"])
                ax.set_xlabel("Pitch angle (°)", fontsize=8)
                ax.set_ylabel("Power (kW)", fontsize=8)
                ax.set_ylim(bottom=-50)
                self._apply_axes_style(ax)
            for i in range(len(page_turbines), nrows * ncols):
                axes[i // ncols, i % ncols].set_visible(False)
            chart_id = f"pitch_vs_power_p{page_idx + 1}"
            results.append(self._save(fig, chart_id, f"Pitch angle vs power scatter page {page_idx + 1}"))
        return results


def build_wind_report_assets(*, config: dict, analysis: dict, assets_dir: Path) -> dict:
    return WindChartFactory(config=config, analysis=analysis, assets_dir=assets_dir).build_all()


def _turbine_intelligence_page(config: dict) -> dict | None:
    """Build a report page from the turbine knowledge base for the site turbine model."""
    if not _KB_AVAILABLE:
        return None
    manufacturer = config.get("turbine_manufacturer", "nordex")
    rated_kw = config.get("rated_power_kw", 0)
    kb = _kb_best_match(manufacturer, rated_kw)
    if not kb:
        return None
    meta = kb["meta"]
    issues = kb.get("known_issues", [])
    strengths = kb.get("strengths", [])
    monitoring = kb.get("monitoring", [])

    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    issues_sorted = sorted(issues, key=lambda i: severity_order.get(i["severity"], 9))

    issue_rows = [
        {
            "Component": i["component"],
            "Known issue": i["issue"][:160] + ("…" if len(i["issue"]) > 160 else ""),
            "Severity": i["severity"],
            "Recommendation": i["recommendation"][:160] + ("…" if len(i["recommendation"]) > 160 else ""),
            "_row_class": "row-danger" if i["severity"] == "HIGH" else "row-warning" if i["severity"] == "MEDIUM" else "",
        }
        for i in issues_sorted
    ]

    high_issues = [i for i in issues_sorted if i["severity"] == "HIGH"]
    findings = [
        {
            "title": f"Known weakness — {i['component']}",
            "severity": "danger",
            "body": i["issue"][:220] + ("…" if len(i["issue"]) > 220 else ""),
        }
        for i in high_issues[:3]
    ]

    commentary = [
        f"The {meta['model']} ({meta['drivetrain']}) is documented in the 8.2 turbine knowledge base with {len(issues)} known failure modes across {len({i['component'].split(' –')[0] for i in issues})} distinct component groups.",
        f"HIGH severity items represent failure modes with documented field frequency and significant revenue impact; they should be cross-checked against the fault message log and SCADA trending data presented in this report.",
    ]
    if strengths:
        commentary.append("Design strengths: " + " | ".join(strengths))
    if monitoring:
        commentary.append("Priority monitoring channels for this model: " + "; ".join(monitoring[:5]) + ("…" if len(monitoring) > 5 else "."))

    return {
        "template": "section",
        "id": "turbine-intelligence",
        "toc_group": "Overview",
        "title": f"Turbine Model Intelligence — {meta['model']}",
        "kicker": "OEM knowledge base",
        "summary": f"Known failure modes, component weaknesses, and recommended monitoring priorities for the {meta['model']}.",
        "commentary_title": "Model intelligence summary",
        "commentary": commentary,
        "tables": [
            _table_block(
                f"Known Issues — {meta['model']}",
                ["Component", "Known issue", "Severity", "Recommendation"],
                issue_rows,
            )
        ],
        "figures": [
            {
                "title": f"{meta['model']} — Delta4000 Platform",
                "caption": "Nordex N131 3.9 MW (Delta4000 series). © Nordex SE — used for identification purposes.",
                "src": (Path(__file__).parent / "nordex_n131_delta4000.jpg").as_uri(),
                "width": "full",
                "alt": f"Nordex {meta['model']} wind turbine",
            }
        ] if (Path(__file__).parent / "nordex_n131_delta4000.jpg").exists() else [],
        "kpis": [
            _kpi("Drivetrain", meta["drivetrain"].split("(")[0].strip()),
            _kpi("IEC class", meta.get("iec_class", "n/a")),
            _kpi("Rotor diameter", f"{meta['rotor_m']} m"),
            _kpi("HIGH severity issues", str(len(high_issues)), "Require attention", "danger" if high_issues else "success"),
        ],
        "findings": findings,
        "notes": [],
    }


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
        {"Parameter": "Turbine model", "Value": "Nordex N131 3.9 MW", "Notes": "IEC Class IIA, 131 m rotor diameter, 3,900 kW rated output."},
        {"Parameter": "Analysis period", "Value": f"{analysis['period_start']:%d %b %Y} to {analysis['period_end']:%d %b %Y}", "Notes": "Based on the available 5-minute operation export."},
        {"Parameter": "Fleet size", "Value": str(config["n_turbines"]), "Notes": "Turbines included in the fleet-wide assessment."},
        {"Parameter": "Rated turbine power", "Value": _fmt_num(config["rated_power_kw"], 0, " kW"), "Notes": "Nominal 3,900 kW per Nordex N131 specification."},
        {"Parameter": "Installed capacity", "Value": _fmt_num(config["cap_ac_kw"] / 1000.0, 1, " MW"), "Notes": "Fleet total based on the Nordex N131 3.9 MW rating."},
        {"Parameter": "Sampling interval", "Value": _fmt_num(config["interval_minutes"], 0, " min"), "Notes": "Native SCADA export interval."},
        {"Parameter": "Primary channels", "Value": "Power, wind speed, wind direction, nacelle position, rotor speed, generator speed", "Notes": "Used for data-quality and performance screening."},
        {"Parameter": "Downtime evidence", "Value": "Manufacturer message logs and low-output detection", "Notes": "Used together to distinguish low-wind behaviour from operational downtime."},
        {"Parameter": "Performance reference", "Value": "Fleet-derived reference power curve envelope", "Notes": "Constructed from the upper operating envelope across valid wind-speed bins."},
        {"Parameter": "Loss valuation", "Value": f"€{config['tariff_eur_per_kwh']:.02f}/kWh", "Notes": "Applied to estimated recoverable energy losses in the action register."},
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
    turbine_monthly_avail = analysis.get("availability_monthly_by_turbine", {})
    lc_summary = analysis.get("messages", {}).get("log_code_summary", pd.DataFrame())

    overview_pages = [
        {
            "template": "cover",
            "title": config["report_title"],
            "subtitle": "SCADA Performance Analysis Report",
            "metadata": [
                ("Project", config["site_name"]),
                ("Asset", f"{config['cap_ac_kw'] / 1000.0:,.1f} MW wind farm"),
                ("Analysis period", f"{analysis['period_start']:%d %b %Y} to {analysis['period_end']:%d %b %Y}"),
                ("Technology", f"{config['n_turbines']} x Nordex N131 3.9 MW"),
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
                f"Annualised recoverable value is {_fmt_keur_per_year(losses['recoverable_loss_eur_year'])} ({_fmt_eur_per_year(losses['recoverable_loss_eur_year'])}). {annualisation_note}",
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
                    ["Priority", "Category", "Estimated loss (MWh/y)", "k€/yr", "Action"],
                    [
                        {
                            "Priority": item["priority"],
                            "Category": item["category"],
                            "Estimated loss (MWh/y)": _fmt_num(item["mwh_loss_year"], 1),
                            "k€/yr": _fmt_keur_per_year(item["eur_loss_year"]),
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
                _kpi("Recoverable value", _fmt_keur_per_year(losses["recoverable_loss_eur_year"]), annualisation_note, "danger" if losses["recoverable_loss_eur_year"] >= 5000 else "warning"),
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
                f"{config['site_name']} comprises {config['n_turbines']} Nordex N131 3.9 MW turbines (131 m rotor, IEC Class IIA) with a total installed capacity of {_fmt_num(config['cap_ac_kw'] / 1000.0, 1, ' MW')}.",
                "This first-pass WINDPAT assessment uses fleet operation data and manufacturer messages to screen telemetry quality, estimate wind-resource capture, quantify availability-led losses, and prioritise corrective actions.",
                "The Nordex N131 has a design cut-in wind speed of approximately 3 m/s, rated wind speed around 13 m/s, and cut-out at 20 m/s. The fleet-derived reference power curve is benchmarked against this operating envelope; scatter points above 20 m/s with fewer than 12 observations per bin are excluded from the reference to avoid storm-mode artefacts.",
                f"Geographic siting is shown from the supplied KMZ marker at {site_location['latitude']:.4f} N, {site_location['longitude']:.4f} E."
                if site_location.get("latitude") is not None and site_location.get("longitude") is not None
                else "No site KMZ marker was available, so the geographic locator panel is omitted.",
            ],
            "kpis": [
                _kpi("Installed capacity", _fmt_num(config["cap_ac_kw"] / 1000.0, 1, " MW")),
                _kpi("Turbines analysed", str(config["n_turbines"])),
                _kpi("Reporting interval", _fmt_num(config["interval_minutes"], 0, " min")),
                _kpi("Tariff assumption", f"€{config['tariff_eur_per_kwh']:.02f}/kWh"),
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
                "The table below consolidates the site configuration and the analysis assumptions used to translate raw 5-minute SCADA streams into fleet-level performance and loss indicators.",
                "The turbine layout map shows the GPS position of each wind turbine and the delivery substation (Poste de livraison). Background: Esri WorldImagery satellite layer.",
            ],
            "tables": [
                _table_block("Site And SCADA Basis", ["Parameter", "Value", "Notes"], tech_rows_a),
                _table_block("Diagnostic Assumptions", ["Parameter", "Value", "Notes"], tech_rows_b),
            ],
            "figures": [
                fig for fig in [
                    _figure_block(charts, "turbine_layout_map", "LUCE II — Turbine Layout",
                                  "GPS coordinates for each turbine and the delivery substation. Esri WorldImagery satellite background.", width="full")
                ] if fig
            ],
            "kpis": [],
            "findings": [],
            "notes": [],
        },
        *([_turbine_intelligence_page(config)] if _turbine_intelligence_page(config) else []),
    ]

    turbines_sorted = sorted(
        analysis["power_curve"].get("scatter_by_turbine", analysis["power_curve"]["binned_by_turbine"]).keys(),
        key=_sort_key,
    )

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
                "Turbines showing noticeably lower completeness than the fleet average should be checked first: a persistent gap in power reporting may mask genuine underperformance, while a persistent gap in wind-speed data makes individual power-curve benchmarking unreliable for that unit. Either case should be raised with the SCADA integrator before the next contractual performance review.",
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
                f"The fleet performance index of {_fmt_pct(perf['fleet_performance_index_pct'])} indicates how much of the derived reference energy envelope was captured. Comparing monthly energy with mean wind speed makes it easier to separate true technical underperformance from simple wind-resource seasonality.",
                f"Peak production months (Apr 2024: {_fmt_num(perf['monthly']['energy_mwh'].max(), 0, ' MWh')}) align with the strongest wind months, confirming the fleet responds broadly to the wind resource. However, months with high wind speed but below-expected energy warrant investigation for curtailment or availability losses.",
                f"Note on the final bar in the chart: the SCADA dataset ends on {analysis['period_end']:%d %b %Y}, so the last calendar month is a partial observation (only {max(1, int((analysis['period_end'] - analysis['period_end'].replace(day=1)).total_seconds() / 86400) + 1)} days). The mean wind speed for that truncated window ({_fmt_num(float(perf['monthly']['wind_speed_ms'].iloc[-1]), 1, ' m/s')}) is measured over the same short period and happened to be unusually high — creating a visible gap against the low partial-month energy. This is a data-boundary artefact, not a technical failure.",
            ],
            "figures": [
                _figure_block(charts, "monthly_energy_cf", "Monthly Energy And Mean Wind Speed", "Monthly energy bars are overlaid with mean wind speed so lower production can be compared directly against the wind regime.", width="full"),
                _figure_block(charts, "daily_specific_yield", "Daily Specific Yield And 30-day Rolling Mean", "The rolling mean shows whether production weakness is persistent rather than driven by isolated trip days.", width="full"),
            ],
            "tables": [],
            "kpis": [],
            "findings": [
                {
                    "title": "Last month artefact",
                    "severity": "info" if True else "info",
                    "body": f"The final month in the chart ({analysis['period_end']:%b %Y}) is a partial period ending {analysis['period_end']:%d %b %Y}. The apparent wind-speed/energy gap is a dataset truncation effect — do not interpret as curtailment or underperformance.",
                }
            ],
            "notes": [],
        },
        {
            "template": "section",
            "id": "fleet-comparison",
            "toc_group": "Main Report",
            "paginate": False,
            "title": "Fleet Turbine Comparison",
            "kicker": "Relative ranking",
            "summary": "Availability and performance-index comparison across the four turbines.",
            "commentary_title": "Fleet interpretation",
            "commentary": [
                "The scatter separates turbines that are mainly downtime-driven (left side of the chart, low availability) from those that remain available but convert wind resource less efficiently than the fleet envelope (lower PI, high availability).",
                f"Turbines in the lower-left quadrant (availability < 95%, PI < 95%) are the highest-priority intervention targets as they carry both an uptime and an efficiency deficit simultaneously. {top_exposed_turbine} currently shows the highest annualised recoverable exposure.",
                "Turbines with good availability but low PI often indicate blade pitch mis-calibration, nacelle misalignment, or a deteriorating gearbox — issues that do not trigger hard faults but gradually erode the power curve. These should be scheduled for a blade inspection and pitch audit during the next maintenance window.",
            ],
            "figures": [_figure_block(charts, "fleet_comparison", "Performance Index Versus Availability", "Lower-left points warrant immediate intervention because both uptime and energy capture are weak.", width="full")],
            "tables": [
                _table_block(
                    "Lowest Performing Turbines",
                    ["Turbine", "Availability", "Performance index", "Recoverable loss", "k€/yr"],
                    [
                        {
                            "Turbine": turbine,
                            "Availability": _fmt_pct(row["availability_pct"]),
                            "Performance index": _fmt_pct(row["performance_index_pct"]),
                            "Recoverable loss": _fmt_num(row["recoverable_mwh_year"], 1, " MWh/yr"),
                            "k€/yr": _fmt_keur_per_year(row["recoverable_eur_year"]),
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
            "paginate": False,
            "title": "Availability And Reliability",
            "kicker": "Operational continuity",
            "summary": "Monthly availability and dominant downtime drivers from the message logs.",
            "commentary_title": "Reliability interpretation",
            "commentary": [
                f"Site availability averaged {_fmt_pct(availability['site_availability_pct'])}. Recurring manufacturer-status messages were screened to separate genuine technical stoppages from low-wind idle conditions.",
                f"A fleet availability below 95% during high-wind months has an outsized revenue impact because each lost hour corresponds to near-rated production. Any month where availability drops below 90% should be cross-checked against the fault message logs to confirm whether a single extended outage or repeated short trips drove the deficit.",
                "Persistent recurrence of the same fault family across several turbines usually indicates either a common subsystem weakness or a fleet-wide maintenance practice issue rather than an isolated unit event. Contrarily, single-turbine recurring faults point to unit-specific mechanical or sensor degradation.",
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
                f"Recoverable losses total {_fmt_num(losses['recoverable_loss_mwh'], 0, ' MWh')} over the analysed period, equivalent to {_fmt_keur_per_year(losses['recoverable_loss_eur_year'])} annualised.",
                "Availability loss quantifies periods where the wind resource was present but one or more turbines were effectively unavailable. Performance loss captures sub-envelope operation after excluding those clear downtime periods.",
                f"{'Availability loss dominates the total shortfall — maintenance response speed and recurring-trip resolution carry the highest return on intervention.' if losses['availability_loss_mwh'] >= losses['performance_loss_mwh'] else 'Performance loss is the larger component — turbines are broadly available but are not converting the wind resource at the reference envelope rate. Blade, pitch, and yaw-alignment investigations should take priority.'}",
                "The waterfall chart makes it easier to communicate the loss structure to asset owners: start from potential energy, subtract availability loss (controllable via maintenance), then performance loss (controllable via optimisation), and the residual is unexplained shortfall that may warrant deeper investigation.",
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
                f"The punchlist ranks actions by annualised recoverable revenue. {annualisation_note}",
                "HIGH priority items carry the largest revenue exposure and should be addressed within the current maintenance cycle. MEDIUM items represent incremental gains that accumulate meaningfully over a 12-month horizon and should be included in the next planned service visit.",
                "Where multiple actions target the same turbine, sequence them to minimise repeated access trips — grouping field work by unit reduces logistics overhead and improves contractor efficiency.",
            ],
            "tables": [
                _table_block(
                    "Full Action Punchlist",
                    ["Priority", "Category", "Issue", "Recommended action", "Estimated loss (MWh/y)", "k€/yr"],
                    [
                        {
                            "Priority": item["priority"],
                            "Category": item["category"],
                            "Issue": item["issue"],
                            "Recommended action": item["action"],
                            "Estimated loss (MWh/y)": _fmt_num(item["mwh_loss_year"], 1),
                            "k€/yr": _fmt_keur_per_year(item["eur_loss_year"]),
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
        *[
            {
                "template": "appendix",
                "id": "appendix-power-curve",
                "toc_group": "Appendix",
                "toc_hide": page_idx > 0,
                "title": "Appendix - Fleet Power Curve Diagnostics",
                "summary": "Scatter of all 10-minute operating points per turbine against the fleet reference curve. Orange points indicate potential curtailment." if page_idx == 0 else "",
                "commentary": [],
                "figures": [fig for fig in [
                    _figure_block(charts, f"power_curve_scatter_p{page_idx + 1}",
                                  f"Power Curve Scatter — {', '.join(turbines_sorted[page_idx*4:(page_idx+1)*4])}",
                                  "Blue = normal operating points. Orange = potential curtailment (wind ≥ 6 m/s, power < 75% of reference).",
                                  width="full")
                ] if fig],
                "tables": [],
                "findings": [],
                "notes": [],
            }
            for page_idx in range(ceil(len(turbines_sorted) / 4))
        ],
        {
            "template": "appendix",
            "id": "appendix-performance-index",
            "toc_group": "Appendix",
            "title": "Appendix - Turbine Performance Index",
            "summary": "Ratio of actual energy to reference-curve potential, annualised over the full analysis period.",
            "commentary": [],
            "figures": [fig for fig in [_figure_block(charts, "performance_index", "Performance Index By Turbine", "Turbines below 95% are flagged for investigation. Red < 90%, amber 90–95%, blue ≥ 95%.", width="full")] if fig],
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
        # ── NEW APPENDIX 1: Monthly Availability Per Turbine ─────────────────
        {
            "template": "appendix",
            "id": "appendix-monthly-availability",
            "toc_group": "Appendix",
            "title": "Appendix - Monthly Availability Per Turbine",
            "summary": "Heat map of per-turbine monthly technical availability over the full analysis period. Green = high availability, red = low.",
            "commentary": [
                "Formula: Availability (%) = (eligible intervals where turbine was available) / (total eligible intervals) × 100. An interval is 'eligible' when the fleet reference power at the measured wind speed exceeds 15% of rated power — this filters out low-wind idle periods so the metric reflects true technical uptime.",
                "Month-over-month variation within a single turbine helps distinguish one-off events (sudden isolated dip) from progressive degradation (gradual multi-month decline). A dip that spans only one turbine in a given month points to a unit-specific fault, while a fleet-wide dip in the same month is more likely driven by a site-wide event or seasonal low-wind bias in the calculation.",
            ],
            "figures": [
                fig for fig in [
                    _figure_block(charts, "monthly_availability_heatmap",
                                  "Monthly Technical Availability By Turbine",
                                  "Colour scale: green ≥ 98%, amber ~90-98%, red ≤ 90%. Grey cells = insufficient eligible intervals that month.",
                                  width="full")
                ] if fig
            ],
            "tables": [],
            "findings": [],
            "notes": [
                "Colour scale is anchored at 80% (red) to 100% (green). Months with no wind-eligible intervals are masked and shown as grey."
            ],
        },
        # ── NEW APPENDIX 2: Fault Log Code Summary ───────────────────────────
        {
            "template": "appendix",
            "id": "appendix-fault-log-codes",
            "toc_group": "Appendix",
            "paginate": False,
            "title": "Appendix - Fault Log Code Frequency Summary",
            "summary": "Top 10 most frequent manufacturer error codes ranked by event count, with category mapping and potential issue guidance.",
            "commentary": [
                "Error codes are grouped from the raw manufacturer message export. The frequency count reflects the number of distinct start/stop events, not the total duration. High-frequency short-duration codes often point to nuisance tripping or sensor instability, while low-frequency but long-duration codes flag hard mechanical faults.",
                "The 'Potential Issue' column provides a first-pass diagnostic interpretation based on the error category. These interpretations should be validated against the OEM service manual and the specific turbine's maintenance history before scheduling corrective work.",
                "Category mapping: Electrical faults typically involve the converter, inverter, or transformer; Grid faults are usually triggered by external grid events outside the operator's control; Mechanical faults involve drivetrain, bearing, or structural components; Control faults cover sensor and software anomalies; Safety faults are highest-priority as they may involve emergency stop activation.",
            ],
            "figures": [],
            "tables": [
                _table_block(
                    "Error Code Frequency — Top 10",
                    ["Error #", "Error Text", "Category", "Count", "Total Duration (h)", "Potential Issue"],
                    [
                        {
                            "Error #": str(row["Error number"]),
                            "Error Text": str(row["Error text"])[:120] + ("…" if len(str(row["Error text"])) > 120 else "") if pd.notna(row["Error text"]) else "—",
                            "Category": str(row["Category"]) if pd.notna(row["Category"]) else "Unclassified",
                            "Count": _fmt_num(row["count"], 0),
                            "Total Duration (h)": _fmt_num(row["total_duration_h"], 1),
                            "Potential Issue": (
                                "Inverter or converter fault; may require component replacement or thermal inspection"
                                if str(row["Category"]).lower() in ("electrical", "electric")
                                else "Grid event or frequency deviation; check grid operator logs and protection relay settings"
                                if str(row["Category"]).lower() in ("grid", "network")
                                else "Bearing, gearbox or drivetrain issue; schedule vibration analysis and lubrication check"
                                if str(row["Category"]).lower() in ("mechanical", "mechanic")
                                else "Control system or sensor fault; check calibration, wiring continuity, and firmware version"
                                if str(row["Category"]).lower() in ("control", "controller", "software")
                                else "Safety system activation; review emergency stop log and verify reset procedure compliance"
                                if str(row["Category"]).lower() in ("safety", "emergency")
                                else "Pitch system fault; inspect pitch drive, battery backup, and blade bearing clearance"
                                if str(row["Category"]).lower() in ("pitch",)
                                else "Yaw or nacelle alignment fault; check yaw drive motor and position sensor"
                                if str(row["Category"]).lower() in ("yaw", "nacelle")
                                else "Communication or SCADA link fault; verify network hardware and data logger connectivity"
                                if str(row["Category"]).lower() in ("communication", "scada", "remote")
                                else "Unclassified — review error text for root cause and cross-reference OEM fault code table"
                            ),
                            "_row_class": "row-warning" if row["count"] >= 10 else "",
                        }
                        for _, row in lc_summary.iterrows()
                    ] if not lc_summary.empty else [],
                    caption="Error codes ranked by frequency. Duration = cumulative hours across all events of that code.",
                    appendix_only=True,
                )
            ],
            "findings": [],
            "notes": [
                "Codes with 'Unclassified' category were not mapped to a standard fault category in the SCADA export. Cross-reference the OEM fault code table to assign the correct subsystem."
            ],
        },
        # ── NEW APPENDIX 3: Wind Roses ────────────────────────────────────────
        {
            "template": "appendix",
            "id": "appendix-wind-roses",
            "toc_group": "Appendix",
            "title": "Appendix - Wind Rose By Turbine",
            "summary": "Wind rose diagrams showing the frequency and speed distribution of wind by direction sector for each turbine.",
            "commentary": [
                "Each rose panel shows the percentage of time the wind blew from each 30° directional sector, coloured by wind speed band. The dominant sector(s) with the tallest bars represent the prevailing wind regime at the nacelle anemometer.",
                "Wake interaction: when multiple turbines share the same dominant wind sector and are aligned along that direction, upstream turbines will shadow downstream units. The resulting wake deficit typically reduces wind speed by 5–15% at the downstream rotor, causing measurable production losses and increased fatigue loading. Compare the rose patterns across turbines to identify potential wake corridors.",
                "Terrain channelling: a sector where wind speed is consistently higher than other directions (darker blue shading concentrated in one direction) may indicate local terrain funnelling. This can increase energy capture but also elevates extreme-load risk if not accounted for in the fatigue design basis.",
                "Yaw alignment: where the wind rose shows a broad spread across multiple sectors of similar frequency, the yaw system demands are higher and misalignment errors are more costly. A turbine with a flat (uniform) rose profile should receive priority attention during yaw calibration checks.",
            ],
            "figures": [
                fig for fig in [
                    _figure_block(charts, "wind_roses_all_turbines", "Wind Rose By Turbine",
                                  "Each panel shows directional frequency (bar length) with wind speed colouring. Dominant sectors correspond to prevailing wind directions.", width="full")
                ] if fig
            ],
            "tables": [],
            "findings": [],
            "notes": [
                "Wind rose data is sampled at up to 8,000 points per turbine for chart clarity. Directional bins are 30° wide centred on the cardinal and intercardinal headings."
            ],
        },
        # ── NEW APPENDIX 4: Rotor RPM vs Power ───────────────────────────────
        *([
            {
                "template": "appendix",
                "id": "appendix-rpm-vs-power",
                "toc_group": "Appendix",
                "toc_hide": page_idx > 0,
                "title": "Appendix - Rotor RPM vs Power",
                "summary": "Scatter of rotor speed against electrical power output for each turbine. Deviations from the expected RPM-power locus indicate mechanical, control, or sensor anomalies." if page_idx == 0 else "",
                "commentary": [
                    "At partial load (below rated wind speed), rotor speed should increase proportionally with wind speed as the turbine operates on the optimal tip-speed-ratio curve. In this region, the RPM-power scatter should follow a smooth cubic-like locus — low RPM at low power, rising to rated RPM just before rated power.",
                    "Above rated power, the pitch control system activates to hold rotor speed near constant while maintaining rated output. This shows in the scatter as a vertical cluster of points at rated power across a narrow RPM band.",
                    "Diagnostic flags: (1) Clusters of low-power points at normal rotor RPM suggest active curtailment or a power conversion fault rather than a wind-resource deficit. (2) Very low RPM at wind speeds that should produce partial-load output may indicate mechanical drag from a seized bearing or high drivetrain friction. (3) A scatter that wraps above rated power at normal RPM indicates boost-mode operation or a power measurement offset in the SCADA historian.",
                    "RPM sensor health: erratic scatter with vertically striped bands often points to a faulty speed encoder or pulse-counter resolution issue rather than actual mechanical behaviour.",
                ] if page_idx == 0 else [],
                "figures": [
                    fig for fig in [
                        _figure_block(
                            charts,
                            f"rpm_vs_power_p{page_idx + 1}",
                            f"Rotor RPM vs Power — {', '.join(sorted(analysis.get('rpm_scatter_data', {}).keys(), key=_sort_key)[page_idx*4:(page_idx+1)*4])}",
                            "Scatter coloured by power fraction (light = low power, dark = rated). Points should follow a smooth locus from bottom-left (low wind) to top-right (rated power).",
                            width="full"
                        )
                    ] if fig
                ],
                "tables": [],
                "findings": [],
                "notes": [],
            }
            for page_idx in range(ceil(len(analysis.get("rpm_scatter_data", {})) / 4))
        ] if analysis.get("rpm_scatter_data") else [
            {
                "template": "appendix",
                "id": "appendix-rpm-vs-power",
                "toc_group": "Appendix",
                "title": "Appendix - Rotor RPM vs Power",
                "summary": "RPM vs power data was not available in this SCADA export.",
                "commentary": ["The rotor speed channel (Rotor speed [1/min]) contained no valid positive values. Confirm the SCADA historian is logging the correct register for this turbine model."],
                "figures": [],
                "tables": [],
                "findings": [],
                "notes": [],
            }
        ]),
        # ── NEW APPENDIX 6: Pitch Angle vs Power ─────────────────────────────
        *([
            *[
                {
                    "template": "appendix",
                    "id": "appendix-pitch-vs-power",
                    "toc_group": "Appendix",
                    "toc_hide": page_idx > 0,
                    "title": "Appendix - Pitch Angle vs Power",
                    "summary": "Scatter of blade pitch angle against electrical power output. The pitch control trajectory reveals whether the pitch system is operating as designed across the full power range." if page_idx == 0 else "",
                    "commentary": [
                        "Below rated power: in the partial-load region the pitch angle should remain near fine pitch (typically 0° to 5°), with power increasing as wind speed and rotor RPM rise. In this region, pitch is essentially fixed and power is controlled by varying rotor speed. A cluster of off-pitch (>10°) points at low power may indicate a stuck pitch actuator, a pitch calibration offset, or aggressive storm-approach feathering.",
                        "Above rated power: as wind speed exceeds rated, the pitch control system feathers the blades (increases pitch angle towards 90°) to limit rotor torque and maintain rated output. The scatter should show a broad spread of pitch angles (5° to 25°+) concentrated in the rated power band. The rate of pitch increase with wind speed depends on the turbine's control algorithm and the instantaneous wind turbulence.",
                        "Diagnostic flags: (1) Points at rated power with near-zero pitch suggest the pitch loop is inactive or the SCADA pitch channel is logging the fine-pitch stop position instead of the actual blade angle. (2) Large pitch angles (>15°) at sub-rated power may indicate active curtailment, noise-optimised reduced-power mode, or a pitch runaway event. (3) Asymmetric scatter between blades (if individual blade angles are logged) can indicate a failed pitch motor or differential blade wear.",
                        "Note: pitch angle measurement conventions vary by OEM. Nordex N131 uses positive pitch = feathering direction. A value near 0° is fine pitch (maximum chord facing wind); a value near 90° is fully feathered (blade edge facing wind).",
                    ] if page_idx == 0 else [],
                    "figures": [
                        fig for fig in [
                            _figure_block(
                                charts,
                                f"pitch_vs_power_p{page_idx + 1}",
                                f"Pitch Angle vs Power — {', '.join(sorted(analysis.get('pitch_scatter_data', {}).keys(), key=_sort_key)[page_idx*4:(page_idx+1)*4])}",
                                "Scatter coloured by power fraction. Below rated: pitch should be near 0°–5°. Above rated: pitch increases to feather (5°–25°+) to maintain rated output.",
                                width="full"
                            )
                        ] if fig
                    ],
                    "tables": [],
                    "findings": [],
                    "notes": [],
                }
                for page_idx in range(ceil(len(analysis.get("pitch_scatter_data", {})) / 4))
            ]
        ] if analysis.get("pitch_scatter_data") else [
            {
                "template": "appendix",
                "id": "appendix-pitch-vs-power",
                "toc_group": "Appendix",
                "title": "Appendix - Pitch Angle vs Power",
                "summary": "Pitch angle data was not available in this SCADA export.",
                "commentary": [
                    "No pitch angle channel was found in the SCADA operation data files. The following column names were searched and not found: 'Pitch angle [°]', 'Pitch angle blade A [°]', 'Blade pitch angle [°]', 'Mean pitch [°]'.",
                    "To enable this appendix in future reports, confirm with the SCADA integrator which column name is used for the collective or blade-A pitch angle in the operation data export, and add it to the loader mapping in windpat_scada_analysis.py.",
                ],
                "figures": [],
                "tables": [],
                "findings": [],
                "notes": [],
            }
        ]),
        # ── LAST APPENDIX: Analytical Scope & Data Limitations ───────────────
        {
            "template": "appendix",
            "id": "appendix-limitations",
            "toc_group": "Appendix",
            "title": "Appendix - Analytical Scope And Data Limitations",
            "summary": "Summary of the analytical scope completed for this assessment and the principal data constraints affecting further interpretation.",
            "tables": [
                _table_block(
                    "Analytical Scope Completed",
                    ["Activity", "Status", "Notes"],
                    [
                        {"Activity": "Data availability assessment", "Status": "Completed", "Notes": "Per-turbine and fleet-level SCADA completeness reviewed across all channels.", "_row_class": "row-success"},
                        {"Activity": "Fleet performance index", "Status": "Completed", "Notes": "Power output benchmarked against a fleet-derived reference envelope across wind-speed bins.", "_row_class": "row-success"},
                        {"Activity": "Availability and reliability review", "Status": "Completed", "Notes": "Fleet and per-turbine uptime calculated; recurring downtime families ranked by duration.", "_row_class": "row-success"},
                        {"Activity": "Fault log code analysis", "Status": "Completed", "Notes": "Top-10 error codes ranked by frequency and total downtime duration.", "_row_class": "row-success"},
                        {"Activity": "Loss attribution", "Status": "Completed", "Notes": "Availability-led and performance-led losses quantified and annualised.", "_row_class": "row-success"},
                        {"Activity": "Wind resource assessment", "Status": "Completed", "Notes": "Wind roses and directional frequency distributions generated per turbine.", "_row_class": "row-success"},
                        {"Activity": "Rotor RPM vs power", "Status": "Completed" if analysis.get("rpm_scatter_data") else "Not possible", "Notes": "Rotor speed channel screened for anomalous speed-power trajectory." if analysis.get("rpm_scatter_data") else "Rotor speed channel contained no valid positive values in the SCADA export.", "_row_class": "row-success" if analysis.get("rpm_scatter_data") else "row-warning"},
                        {"Activity": "Pitch angle vs power", "Status": "Completed" if analysis.get("pitch_scatter_data") else "Not possible", "Notes": "Blade pitch angle reviewed against power output across the full operating envelope." if analysis.get("pitch_scatter_data") else "No pitch angle column was found in the SCADA export.", "_row_class": "row-success" if analysis.get("pitch_scatter_data") else "row-warning"},
                        {"Activity": "Monthly availability heatmap", "Status": "Completed", "Notes": "Per-turbine monthly availability visualised as a colour-coded heatmap.", "_row_class": "row-success"},
                        {"Activity": "Action punchlist", "Status": "Completed", "Notes": "Prioritised corrective actions ranked by annualised recoverable revenue exposure.", "_row_class": "row-success"},
                    ],
                ),
                _table_block(
                    "Analyses Not Possible — Data Constraints",
                    ["Analysis", "Status", "Notes"],
                    [
                        {"Analysis": "Independent reference power curve", "Status": "Not possible", "Notes": "No OEM contractual power curve or independent met-mast wind measurement is available. The reference envelope is fleet-derived and may not capture true performance guarantees.", "_row_class": "row-danger"},
                        {"Analysis": "Individual blade pitch angles", "Status": "Not possible" if not analysis.get("pitch_scatter_data") else "Limited", "Notes": "Only collective or blade-A pitch angle may be available. Independent blade-B and blade-C channels are required for imbalance detection between blades.", "_row_class": "row-danger" if not analysis.get("pitch_scatter_data") else "row-warning"},
                        {"Analysis": "Curtailment certainty", "Status": "Limited", "Notes": "Without explicit grid-export limit flags or setpoint channels in the SCADA, curtailment periods are identified heuristically and may include high-wind cut-out events.", "_row_class": "row-warning"},
                        {"Analysis": "Vibration and structural loads", "Status": "Not possible", "Notes": "No accelerometer, CMS (condition monitoring), or tower strain-gauge data is included in the SCADA export.", "_row_class": "row-danger"},
                        {"Analysis": "Gearbox / drivetrain diagnostics", "Status": "Not possible", "Notes": "Generator speed and rotor speed channels are present but no oil temperature, vibration spectrum, or CMS alarm channels are available for drivetrain health assessment.", "_row_class": "row-danger"},
                        {"Analysis": "Degradation trend", "Status": "Limited", "Notes": "The available time horizon may be insufficient for a statistically robust multi-year performance degradation estimate.", "_row_class": "row-warning"},
                        {"Analysis": "Wake loss quantification", "Status": "Limited", "Notes": "Individual turbine wind speed channels allow qualitative wake screening only. Precise wake-loss modelling requires a validated flow model and free-stream reference.", "_row_class": "row-warning"},
                        {"Analysis": "Short-interval transients", "Status": "Limited", "Notes": "The native SCADA sampling interval is too coarse to isolate sub-interval trip events or ride-through fault signatures.", "_row_class": "row-warning"},
                    ],
                ),
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
