from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

try:
    import check_chart_bounds
except Exception:  # pragma: no cover - best effort
    check_chart_bounds = None


def build_report_assets(*, config: dict, analysis: dict, assets_dir: Path) -> dict:
    factory = ReportChartFactory(config=config, analysis=analysis, assets_dir=assets_dir)
    return factory.build_all()


class ReportChartFactory:
    def __init__(self, *, config: dict, analysis: dict, assets_dir: Path) -> None:
        self.config = config
        self.analysis = analysis
        self.assets_dir = assets_dir
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.tokens = config["style_tokens"]["colors"]
        self.sizes = config["style_tokens"]["chart"]
        self.sort_key = config["sort_key"]
        plt.rcParams.update(
            {
                "axes.titlesize": 12,
                "axes.labelsize": 10.5,
                "xtick.labelsize": 9.5,
                "ytick.labelsize": 9.5,
                "legend.fontsize": 9.5,
            }
        )

    def build_all(self) -> dict:
        charts = {}
        builders = [
            self.chart_site_map,
            self.chart_data_availability_overview,
            self.chart_data_availability_heatmap,
            self.chart_irradiance_monthly_comparison,
            self.chart_irradiance_scatter,
            self.chart_weather_correlation,
            self.chart_monthly_pr_energy,
            self.chart_daily_specific_yield,
            self.chart_inverter_pr_vs_availability,
            self.chart_specific_yield_heatmap,
            self.chart_availability_trend,
            self.chart_waterfall,
            self.chart_monthly_availability_loss,
            self.chart_mttf_failures,
            self.chart_mttf_days,
            self.chart_start_stop,
            self.chart_clipping,
        ]
        for builder in builders:
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

    def _save_png(self, fig, chart_id: str, alt: str) -> dict:
        path = self.assets_dir / f"{chart_id}.png"
        fig.savefig(path, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return {"id": chart_id, "path": str(path), "alt": alt}

    def _save(self, fig, chart_id: str, alt: str) -> dict:
        path = self.assets_dir / f"{chart_id}.svg"
        fig.savefig(path, format="svg", dpi=160, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        if check_chart_bounds is not None:
            check_chart_bounds.validate_chart_asset(path)
        return {"id": chart_id, "path": str(path), "alt": alt}

    def chart_site_map(self) -> dict:
        """Stylised dot-grid map of France with highlighted site point."""
        import math
        from matplotlib.path import Path as MplPath

        LAT = 44.0 + 41.0 / 60.0 + 8.3 / 3600.0    # 44.6856°N
        LON = -(0.0 + 33.0 / 60.0 + 34.0 / 3600.0)  # −0.5594°W

        # ── France mainland polygon (lon, lat) ────────────────────────────
        france = np.array([
            (-4.70, 48.38),  # Brest
            (-4.78, 47.96),  # Brittany SW tip
            (-4.30, 47.80),  # Brittany S
            (-3.50, 47.55),
            (-2.80, 47.50),  # Loire-Atlantique
            (-2.20, 47.25),
            (-1.55, 47.10),
            (-1.20, 46.40),  # Vendée
            (-1.10, 45.70),  # Charente-Maritime
            (-1.10, 44.60),  # Landes
            (-1.80, 43.40),  # Basque coast
            ( 0.30, 43.00),  # Pyrenees centre
            ( 1.60, 42.80),
            ( 3.00, 42.65),  # Roussillon
            ( 3.10, 43.10),
            ( 4.00, 43.20),
            ( 5.05, 43.33),
            ( 5.35, 43.30),  # Marseille
            ( 6.20, 43.10),
            ( 7.40, 43.70),  # Nice
            ( 7.05, 44.10),
            ( 6.90, 45.85),  # Mont Blanc
            ( 6.80, 46.15),
            ( 6.05, 46.42),  # Jura
            ( 7.60, 47.58),  # Basel
            ( 7.80, 48.55),  # Strasbourg
            ( 7.60, 49.00),
            ( 6.35, 49.45),  # Luxembourg
            ( 5.90, 49.50),
            ( 4.10, 50.00),
            ( 3.15, 50.72),  # Belgian border
            ( 2.55, 51.00),  # Dunkirk
            ( 1.60, 50.87),  # Calais
            ( 0.40, 50.05),
            ( 0.20, 49.70),  # Normandy
            (-1.55, 49.68),  # Cherbourg tip
            (-1.55, 49.20),
            (-2.00, 48.70),
            (-3.20, 48.80),
            (-4.70, 48.38),  # back to Brest
        ])

        france_path = MplPath(france)

        # ── Dot grid — visually square given lat distortion at ~47°N ─────
        mean_lat_rad = math.radians(47.0)
        lon_step = 0.38
        lat_step = lon_step * math.cos(mean_lat_rad)   # ~0.259°

        xs = np.arange(-5.5, 9.5, lon_step)
        ys = np.arange(41.8, 51.8, lat_step)
        xx, yy = np.meshgrid(xs, ys)
        pts = np.column_stack([xx.ravel(), yy.ravel()])
        inside = france_path.contains_points(pts)
        dx, dy = pts[inside, 0], pts[inside, 1]

        # ── Figure ────────────────────────────────────────────────────────
        asp = 1.0 / math.cos(mean_lat_rad)   # ~1.47
        fig, ax = plt.subplots(figsize=(7.2, 7.2))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        # France dots
        ax.scatter(dx, dy, s=18, color="#2D3748", alpha=0.75,
                   linewidths=0, zorder=2)

        # Site dot — prominent red with outer ring
        ax.scatter([LON], [LAT], s=220, color=self.tokens["danger_red"],
                   linewidths=2, edgecolors="white", zorder=6)
        ax.scatter([LON], [LAT], s=440, facecolors="none",
                   edgecolors=self.tokens["danger_red"], linewidths=1.2,
                   alpha=0.4, zorder=5)

        # Callout annotation
        ax.annotate(
            "PVPAT Solar PV Farm\n44°41′N  |  0°34′W",
            xy=(LON, LAT),
            xytext=(LON + 3.0, LAT - 1.5),
            fontsize=8.5, fontweight="bold",
            color=self.tokens["primary_navy"], zorder=7,
            arrowprops=dict(
                arrowstyle="->", color=self.tokens["primary_navy"],
                lw=1.0, connectionstyle="arc3,rad=0.2",
            ),
            bbox=dict(
                boxstyle="round,pad=0.38", facecolor="white", alpha=0.93,
                edgecolor=self.tokens["primary_navy"], linewidth=0.9,
            ),
        )

        ax.set_aspect(asp, adjustable="datalim")
        ax.set_xlim(-6.2, 9.8)
        ax.set_ylim(41.0, 52.5)
        ax.axis("off")
        ax.set_title(
            "PVPAT Solar PV Farm  —  Site Location, SW France",
            fontsize=11, fontweight="bold", color=self.tokens["primary_navy"], pad=10,
        )
        return self._save_png(fig, "site_map", "Stylised dot-grid site location map")

    def chart_data_availability_overview(self) -> dict:
        data_avail = self.analysis["data_avail"]
        items = sorted(data_avail["per_inverter"].items(), key=lambda item: self.sort_key(item[0]))
        labels = [name for name, _ in items]
        values = [value for _, value in items]
        fig = plt.figure(figsize=(9.2, 6.7), constrained_layout=True)
        ax1 = fig.add_subplot(111)
        ax1.barh(labels, values, color=self.tokens["secondary_slate_blue"], edgecolor="white")
        ax1.axvline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.1)
        ax1.set_title("Per-Inverter Power Completeness", fontsize=11, fontweight="bold")
        ax1.set_xlabel("Completeness (%)")
        ax1.set_xlim(60, 100)
        ax1.invert_yaxis()
        self._apply_axes_style(ax1)
        ax1.grid(True, axis="x", color=self.tokens["border_grey"], alpha=0.45, linewidth=0.8)
        ax1.grid(False, axis="y")
        ax1.tick_params(axis="y", labelsize=8.6)
        return self._save(fig, "data_availability_overview", "Data availability overview chart")

    def chart_data_availability_heatmap(self) -> dict:
        monthly = pd.DataFrame(self.analysis["data_avail"]["monthly"]).sort_index(axis=1, key=lambda idx: [self.sort_key(item) for item in idx])
        if monthly.empty:
            return {}
        fig = plt.figure(figsize=(7.3, 6.6), constrained_layout=True)
        ax = fig.add_subplot(111)
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        cmap = LinearSegmentedColormap.from_list(
            "dq_heatmap",
            [
                self.tokens["danger_red"],
                self.tokens["accent_orange"],
                "#F4F6F8",
                self.tokens["secondary_slate_blue"],
            ],
        )
        im = ax.imshow(monthly.T.values, aspect="auto", cmap=cmap, vmin=60, vmax=100)
        ax.set_title("Monthly Inverter Completeness Heatmap", fontsize=11, fontweight="bold")
        ax.set_yticks(range(len(monthly.columns)))
        ax.set_yticklabels(list(monthly.columns), fontsize=7)
        ax.set_xticks(range(len(monthly.index)))
        ax.set_xticklabels([ts.strftime("%b\n%y") for ts in monthly.index], fontsize=7)
        self._apply_axes_style(ax)
        fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="Completeness (%)")
        return self._save(fig, "data_availability_heatmap", "Monthly inverter completeness heatmap")

    def chart_irradiance_scatter(self) -> dict | None:
        irr_coh = self.analysis["irr_coh"]
        if not irr_coh:
            return None
        ref_name = sorted(irr_coh)[0]
        metrics = irr_coh[ref_name]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.scatter(metrics["scatter_r"], metrics["scatter_m"], s=6, alpha=0.35, color=self.tokens["secondary_slate_blue"])
        limit = float(max(metrics["scatter_r"].max(), metrics["scatter_m"].max()))
        ax.plot([0, limit], [0, limit], linestyle="--", color=self.tokens["accent_orange"], linewidth=1.1)
        ax.set_title(f"Measured GHI vs SARAH {ref_name}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Reference GHI (W/m²)")
        ax.set_ylabel("Measured GHI (W/m²)")
        self._apply_axes_style(ax)
        return self._save(fig, "irradiance_scatter", "Irradiance scatter comparison")

    def chart_irradiance_monthly_comparison(self) -> dict | None:
        irr_coh = self.analysis["irr_coh"]
        if not irr_coh:
            return None
        refs = sorted(irr_coh.items())
        fig, axes = plt.subplots(len(refs), 1, figsize=(7.2, 5.4), constrained_layout=True)
        if not isinstance(axes, np.ndarray):
            axes = np.array([axes])
        for ax, (name, metrics) in zip(axes, refs):
            dd = metrics["daily_df"].dropna()
            if dd.empty:
                ax.text(0.02, 0.80, f"No valid monthly comparison for SARAH_{name}.", transform=ax.transAxes, fontsize=9, color=self.tokens["muted_text"])
                ax.axis("off")
                continue
            dd = dd.copy()
            dd.index = pd.to_datetime(dd.index)
            measured = dd["measured"].resample("ME").sum()
            reference = dd["reference"].resample("ME").sum()
            bias = (measured - reference) / reference.replace(0, np.nan) * 100
            x = np.arange(len(measured))
            w = 0.35
            ax.bar(x - w / 2, measured.values, w, color=self.tokens["secondary_slate_blue"], alpha=0.9, label="Measured")
            ax.bar(x + w / 2, reference.values, w, color=self.tokens["accent_orange"], alpha=0.8, label=f"SARAH_{name}")
            ax.set_xticks(x)
            ax.set_xticklabels([m.strftime("%b\n%Y") for m in measured.index], fontsize=7)
            ax.set_ylabel("kWh/m²/month")
            ax.set_title(
                f"Monthly GHI Totals vs SARAH_{name} (R={metrics['correlation']:.3f}, ratio={metrics['mean_ratio']:.2f}, suspect={metrics['suspect_pct']:.1f}%)",
                fontsize=10.2,
                fontweight="bold",
            )
            ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
            self._apply_axes_style(ax)
            ax_b = ax.twinx()
            ax_b.plot(x, bias.values, color=self.tokens["danger_red"], linewidth=1.1, marker="o", markersize=3.2, label="Monthly bias")
            ax_b.set_ylabel("Bias (%)", color=self.tokens["danger_red"])
            ax_b.tick_params(axis="y", colors=self.tokens["danger_red"], labelsize=7)
            ax_b.spines["top"].set_visible(False)
            ax_b.spines["right"].set_color(self.tokens["danger_red"])
        return self._save(fig, "irradiance_monthly_comparison", "Monthly irradiance comparison versus SARAH")

    def chart_irradiance_daily(self) -> dict | None:
        irr_coh = self.analysis["irr_coh"]
        if not irr_coh:
            return None
        ref_name = sorted(irr_coh)[0]
        daily_df = irr_coh[ref_name]["daily_df"]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.plot(daily_df.index, daily_df["measured"], color=self.tokens["primary_navy"], linewidth=1.3, label="Measured")
        ax.plot(daily_df.index, daily_df["reference"], color=self.tokens["accent_orange"], linewidth=1.1, label="Reference")
        ax.set_title(f"Daily Irradiance Totals vs SARAH {ref_name}", fontsize=11, fontweight="bold")
        ax.set_ylabel("Daily irradiation (kWh/m²)")
        ax.legend(frameon=False, fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        return self._save(fig, "irradiance_daily", "Daily irradiance comparison")

    def chart_monthly_pr_energy(self) -> dict:
        monthly = self.analysis["pr_res"]["monthly"]
        # Taller figure; manual layout so the third axis has room on the right
        fig, ax1 = plt.subplots(figsize=(9.2, 6.0))
        fig.patch.set_facecolor("white")
        fig.subplots_adjust(left=0.09, right=0.80, top=0.88, bottom=0.18)

        pr_color  = self.tokens["secondary_slate_blue"]   # blue for PR
        irr_color = self.tokens["accent_orange"]           # orange for irradiation

        ax2 = ax1.twinx()   # PR (%)
        ax3 = ax1.twinx()   # Irradiation (kWh/m²)
        ax3.spines["right"].set_position(("outward", 58))

        bars = ax1.bar(
            monthly.index, monthly["E_act"] / 1000.0, width=20,
            color="#B0C4D8", alpha=0.95, zorder=2,
        )
        irr_line = ax3.plot(
            monthly.index, monthly["irrad"],
            color=irr_color, marker="s", markersize=5, linewidth=2.0, zorder=4,
        )[0]
        pr_line = ax2.plot(
            monthly.index, monthly["PR"],
            color=pr_color, marker="o", markersize=5, linewidth=2.0, zorder=5,
        )[0]
        target = ax2.axhline(
            78, color=self.tokens["success_green"], linestyle="--", linewidth=1.1, zorder=3,
        )

        ax1.set_title("Monthly Energy, Irradiation And PR", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Actual energy (MWh)", fontsize=9)
        ax2.set_ylabel("PR (%)", color=pr_color, fontsize=9)
        ax3.set_ylabel("Irradiation (kWh/m²)", color=irr_color, fontsize=9)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))

        self._apply_axes_style(ax1)
        for _ax in (ax2, ax3):
            _ax.spines["top"].set_visible(False)
            _ax.spines["left"].set_visible(False)
            _ax.spines["bottom"].set_visible(False)
        ax2.spines["right"].set_color(pr_color)
        ax2.tick_params(colors=pr_color, labelsize=8)
        ax2.yaxis.label.set_color(pr_color)
        ax3.spines["right"].set_color(irr_color)
        ax3.tick_params(colors=irr_color, labelsize=8)
        ax3.yaxis.label.set_color(irr_color)

        # Legend placed below the plot area — clear of the bars
        ax1.legend(
            [bars, irr_line, pr_line, target],
            ["Energy (MWh)", "Irradiation (kWh/m²)", "PR (%)", "78 % target"],
            frameon=True, framealpha=0.92, edgecolor=self.tokens["border_grey"],
            loc="upper center", bbox_to_anchor=(0.38, -0.13),
            ncol=4, fontsize=8.5,
        )
        return self._save(fig, "monthly_pr_energy", "Monthly energy, irradiation and PR chart")

    def chart_daily_specific_yield(self) -> dict:
        piv = self.analysis["piv"]
        site_pwr = piv.sum(axis=1, min_count=1)
        daily_sy = site_pwr.resample("D").sum() * self.config["interval_h"] / max(self.config["cap_dc_kwp"], 1)
        rolling = daily_sy.rolling(30, center=True).mean()
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.fill_between(daily_sy.index, daily_sy.values, alpha=0.4, color="#DCE7F0", label="Daily specific yield")
        ax.plot(daily_sy.index, daily_sy.values, color=self.tokens["primary_navy"], linewidth=0.8)
        ax.plot(rolling.index, rolling.values, color=self.tokens["danger_red"], linewidth=1.5, label="30-day rolling mean")
        ax.set_ylabel("Specific yield (kWh/kWp/day)")
        ax.set_title("Daily Specific Yield And 30-day Rolling Mean", fontsize=11, fontweight="bold")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        return self._save(fig, "daily_specific_yield", "Daily specific yield time series")

    def chart_inverter_pr(self) -> dict:
        pr_map = self.analysis["pr_res"]["per_inverter"]
        items = sorted(pr_map.items(), key=lambda item: item[1])
        labels = [name for name, _ in items]
        values = [value for _, value in items]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        colors = [self.tokens["danger_red"] if value < 65 else self.tokens["warning_amber"] if value < 75 else self.tokens["secondary_slate_blue"] for value in values]
        ax.bar(labels, values, color=colors, edgecolor="white")
        ax.axhline(75, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax.set_title("Per-Inverter PR Ranking", fontsize=11, fontweight="bold")
        ax.set_ylabel("PR (%)")
        ax.tick_params(axis="x", rotation=60)
        self._apply_axes_style(ax)
        return self._save(fig, "inverter_pr", "Per inverter PR ranking")

    def chart_inverter_pr_vs_availability(self) -> dict:
        pr_map = self.analysis["pr_res"]["per_inverter"]
        av_map = self.analysis["avail_res"]["per_inverter"]
        names = sorted(pr_map, key=self.sort_key)
        x = np.array([av_map.get(name, np.nan) for name in names], dtype=float)
        y = np.array([pr_map.get(name, np.nan) for name in names], dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        if not valid.any():
            return {}
        fleet_mean = float(np.nanmean(y[valid]))
        fleet_std = float(np.nanstd(y[valid]))
        low_pr = y < (fleet_mean - fleet_std)
        low_av = x < 95
        reference = valid & ~(low_pr | low_av)
        low_both = valid & low_pr & low_av
        low_pr_good_av = valid & low_pr & ~low_av
        low_av_only = valid & ~low_pr & low_av
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        legend_specs = [
            ("Reference", reference, self.tokens["secondary_slate_blue"]),
            ("Low PR + low availability", low_both, self.tokens["danger_red"]),
            ("Low PR + good availability", low_pr_good_av, self.tokens["warning_amber"]),
            ("Availability-led underperformance", low_av_only, self.tokens["deep_indigo"]),
        ]
        for label, mask, color in legend_specs:
            if mask.any():
                ax.scatter(x[mask], y[mask], s=40, color=color, alpha=0.88, label=f"{label} ({int(mask.sum())})")
        ax.axvline(95, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax.axhline(75, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        label_candidates = sorted(
            [(names[idx], float(y[idx]), float(x[idx])) for idx in range(len(names)) if valid[idx]],
            key=lambda item: (item[1], item[2]),
        )[:6]
        for name, pr_value, av_value in label_candidates:
            ax.annotate(
                name,
                (av_value, pr_value),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=7.4,
                color=self.tokens["body_text"],
            )
        ax.set_title("PR Versus Availability", fontsize=11, fontweight="bold")
        ax.set_xlabel("Availability (%)")
        ax.set_ylabel("PR (%)")
        self._apply_axes_style(ax)
        ax.legend(frameon=False, fontsize=7.8, loc="lower left")
        return self._save(fig, "inverter_pr_vs_availability", "PR versus availability scatter")

    def chart_weather_correlation(self) -> dict | None:
        weather_data = self.analysis.get("weather_data")
        if weather_data is None:
            return None
        monthly = self.analysis["pr_res"]["monthly"]
        w_dates = pd.to_datetime(weather_data["daily"]["time"])
        w_rain = pd.Series(weather_data["daily"]["precipitation_sum"], index=w_dates, dtype="float64").resample("ME").sum().reindex(monthly.index)
        w_temp = pd.Series(weather_data["daily"]["temperature_2m_max"], index=w_dates, dtype="float64").resample("ME").mean().reindex(monthly.index)
        fig, axes = plt.subplots(2, 1, figsize=(7.25, 10.9), constrained_layout=True)
        ax1, ax2 = axes
        ax1.bar(monthly.index, monthly["PR"], width=20, color=self.tokens["secondary_slate_blue"], alpha=0.9, label="PR")
        ax1b = ax1.twinx()
        ax1b.plot(monthly.index, w_temp, color=self.tokens["danger_red"], linewidth=1.3, marker="o", label="Mean max T")
        ax1b.bar(monthly.index, w_rain, width=20, color="#7DB6D8", alpha=0.35, label="Rain")
        ax1.set_title("Monthly PR, Rainfall, And Temperature", fontsize=11, fontweight="bold")
        ax1.set_ylabel("PR (%)")
        ax1b.set_ylabel("Weather markers")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax1)

        day_df = self.analysis["pr_res"]["df_day"].copy()
        day_df = day_df.resample("D").sum()
        day_df["PR"] = (day_df["E_act"] / day_df["E_ref"].replace(0, np.nan) * 100).clip(0, 110)
        day_df = day_df.join(pd.Series(weather_data["daily"]["temperature_2m_max"], index=w_dates, dtype="float64").rename("tmax"), how="left")
        valid = day_df.dropna(subset=["PR"])
        sc = ax2.scatter(valid.index, valid["PR"], c=valid["tmax"].fillna(20), cmap="coolwarm", s=10, alpha=0.65)
        fig.colorbar(sc, ax=ax2, fraction=0.025, pad=0.02, label="Max temperature (°C)")
        ax2.set_title("Daily PR Coloured By Temperature", fontsize=11, fontweight="bold")
        ax2.set_ylabel("PR (%)")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax2)
        return self._save(fig, "weather_correlation", "Weather correlation chart")

    def chart_specific_yield_heatmap(self) -> dict:
        inv_sy = self.analysis["inv_sy_df"].sort_index(axis=1, key=lambda idx: [self.sort_key(item) for item in idx])
        piv = self.analysis["piv"]
        irr = self.analysis["irr_data"]
        inv_dc_kwp = self.config["cap_dc_kwp"] / max(piv.shape[1], 1)
        ghi_s = irr.set_index("ts")["GHI"].reindex(piv.index)
        ghi_monthly = ghi_s.resample("ME").sum() * self.config["interval_h"] / 1000
        pr_df = (piv * self.config["interval_h"]).resample("ME").sum().divide(ghi_monthly * inv_dc_kwp, axis=0) * 100
        pr_df = pr_df.clip(0, 100).sort_index(axis=1, key=lambda idx: [self.sort_key(item) for item in idx])
        fleet_mean = inv_sy.mean(axis=1)
        dev_pct = inv_sy.subtract(fleet_mean, axis=0).divide(fleet_mean.clip(lower=1), axis=0) * 100
        fig, axes = self._figure("appendix_wide", 2, 1)
        ax1, ax2 = axes
        im1 = ax1.imshow(dev_pct.T.values, aspect="auto", cmap="RdYlBu_r", vmin=-20, vmax=20)
        ax1.set_title("Specific Yield Deviation Vs Fleet Mean", fontsize=11, fontweight="bold")
        ax1.set_yticks(range(len(inv_sy.columns)))
        ax1.set_yticklabels(list(inv_sy.columns), fontsize=7.2)
        ax1.set_xticks(range(len(inv_sy.index)))
        ax1.set_xticklabels([ts.strftime("%b\n%y") for ts in inv_sy.index], fontsize=7.4)
        self._apply_axes_style(ax1)
        fig.colorbar(im1, ax=ax1, fraction=0.025, pad=0.02, label="% vs fleet mean")

        im2 = ax2.imshow(pr_df.T.values, aspect="auto", cmap="RdYlGn", vmin=40, vmax=90)
        ax2.set_title("Monthly PR By Inverter", fontsize=11, fontweight="bold")
        ax2.set_yticks(range(len(pr_df.columns)))
        ax2.set_yticklabels(list(pr_df.columns), fontsize=7.2)
        ax2.set_xticks(range(len(pr_df.index)))
        ax2.set_xticklabels([ts.strftime("%b\n%y") for ts in pr_df.index], fontsize=7.4)
        self._apply_axes_style(ax2)
        fig.colorbar(im2, ax=ax2, fraction=0.025, pad=0.02, label="PR (%)")
        return self._save(fig, "specific_yield_heatmap", "Specific yield and PR heatmaps")

    def chart_availability_trend(self) -> dict:
        monthly = self.analysis["avail_res"]["site_monthly"]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.fill_between(monthly.index, monthly.values, np.minimum(monthly.values.min() - 3, 80), color="#DCE7F0", alpha=0.9)
        ax.plot(monthly.index, monthly.values, color=self.tokens["primary_navy"], linewidth=1.8, marker="o", markersize=4.5)
        ax.axhline(95, color=self.tokens["accent_orange"], linestyle="--", linewidth=1.0)
        ax.set_title("Monthly Site Availability", fontsize=11, fontweight="bold")
        ax.set_ylabel("Availability (%)")
        ax.set_ylim(min(80, monthly.values.min() - 3), 101)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax)
        if len(monthly):
            ax.text(monthly.index[-1], 95.8, "95% target", color=self.tokens["accent_orange"], fontsize=8.2, ha="right", va="bottom")
        return self._save(fig, "availability_trend", "Monthly availability trend")

    def chart_availability_heatmap(self) -> dict:
        monthly = self.analysis["avail_res"]["per_inverter_monthly"].sort_index(axis=1, key=lambda idx: [self.sort_key(item) for item in idx])
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        im = ax.imshow(monthly.T.values, aspect="auto", cmap="YlGn", vmin=70, vmax=100)
        ax.set_title("Per-Inverter Availability Heatmap", fontsize=11, fontweight="bold")
        ax.set_yticks(range(len(monthly.columns)))
        ax.set_yticklabels(list(monthly.columns), fontsize=6.5)
        ax.set_xticks(range(len(monthly.index)))
        ax.set_xticklabels([ts.strftime("%b\n%y") for ts in monthly.index], fontsize=7)
        self._apply_axes_style(ax)
        fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="Availability (%)")
        return self._save(fig, "availability_heatmap", "Availability heatmap")

    def chart_waterfall(self) -> dict:
        wf = self.analysis["wf"]
        labels = ["Budget", "Weather corr.", "Availability loss", "Technical loss", "Residual", "Actual"]
        values = [wf["budget"], wf["weather_corr"], wf["avail_loss"], wf["technical_loss"], wf["residual"], wf["actual"]]
        cumulative = [0, wf["budget"], wf["budget"] + wf["weather_corr"], wf["budget"] + wf["weather_corr"] + wf["avail_loss"], wf["budget"] + wf["weather_corr"] + wf["avail_loss"] + wf["technical_loss"], 0]
        colors = [self.tokens["primary_navy"], self.tokens["secondary_slate_blue"], self.tokens["warning_amber"], self.tokens["danger_red"], self.tokens["deep_indigo"], self.tokens["success_green"]]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        for idx, (label, value, base, color) in enumerate(zip(labels, values, cumulative, colors)):
            if label == "Actual":
                ax.bar(idx, value, color=color, edgecolor="white")
            else:
                ax.bar(idx, value, bottom=base, color=color, edgecolor="white")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.set_title("Energy Loss Waterfall", fontsize=11, fontweight="bold")
        ax.set_ylabel("Energy (MWh)")
        self._apply_axes_style(ax)
        return self._save(fig, "waterfall", "Energy waterfall chart")

    def chart_monthly_availability_loss(self) -> dict:
        monthly_pr = self.analysis["pr_res"]["monthly"]
        site_monthly = self.analysis["avail_res"].get("site_monthly", pd.Series(dtype=float))
        if monthly_pr is None or monthly_pr.empty or site_monthly.empty:
            return None
        budget_mwh = monthly_pr["E_ref"] * self.config["design_pr"] / 1000.0
        avail_pct = site_monthly.reindex(monthly_pr.index).fillna(self.analysis["avail_res"]["mean"])
        avail_loss = (budget_mwh * (1.0 - avail_pct / 100.0)).clip(lower=0)
        colors = [
            self.tokens["danger_red"] if av < 90 else self.tokens["warning_amber"] if av < 95 else self.tokens["secondary_slate_blue"]
            for av in avail_pct.values
        ]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        x = np.arange(len(avail_loss))
        ax.bar(x, avail_loss.values, facecolor="white", edgecolor=colors, linewidth=1.5, width=0.75)
        if len(avail_loss):
            mean_loss = float(avail_loss.mean())
            ax.axhline(mean_loss, color=self.tokens["muted_text"], linestyle="--", linewidth=0.9, alpha=0.75, label=f"Monthly mean {mean_loss:.0f} MWh")
        ax.set_xticks(x)
        ax.set_xticklabels([d.strftime("%b\n%y") for d in avail_loss.index], fontsize=7)
        ax.set_ylabel("Estimated availability loss (MWh)")
        ax.set_title("Monthly Availability Loss Breakdown", fontsize=11, fontweight="bold")
        self._apply_axes_style(ax)
        ax.legend(frameon=False, fontsize=7.6, loc="upper left")
        for idx, (av, value) in enumerate(zip(avail_pct.values, avail_loss.values)):
            ax.text(idx, value + max(float(avail_loss.max()) * 0.02, 0.1), f"{av:.0f}%", ha="center", va="bottom", fontsize=6.8, color=self.tokens["body_text"])
        return self._save(fig, "monthly_availability_loss", "Monthly availability loss breakdown")

    def chart_loss_breakdown(self) -> dict:
        wf = self.analysis["wf"]
        rows = {
            "Availability loss": abs(wf["avail_loss"]),
            "Technical loss": abs(wf["technical_loss"]),
            "Residual": abs(wf["residual"]),
            "Weather correction": abs(wf["weather_corr"]),
        }
        labels = list(rows.keys())
        values = list(rows.values())
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.barh(labels, values, color=[self.tokens["warning_amber"], self.tokens["danger_red"], self.tokens["deep_indigo"], self.tokens["secondary_slate_blue"]])
        ax.set_title("Loss Breakdown", fontsize=11, fontweight="bold")
        ax.set_xlabel("Energy (MWh)")
        self._apply_axes_style(ax)
        return self._save(fig, "loss_breakdown", "Loss breakdown bar chart")

    def chart_mttf_failures(self) -> dict:
        mttf = self.analysis["mttf_res"]
        items = sorted(mttf.items(), key=lambda item: item[1]["n_failures"], reverse=True)[:15]
        fig, ax = self._figure("half")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.bar([name for name, _ in items], [row["n_failures"] for _, row in items], color=self.tokens["danger_red"], edgecolor="white")
        ax.set_title("Top Inverters By Failure Count", fontsize=11, fontweight="bold")
        ax.set_ylabel("Failure events")
        ax.tick_params(axis="x", rotation=60)
        self._apply_axes_style(ax)
        return self._save(fig, "mttf_failures", "Failure count ranking")

    def chart_mttf_days(self) -> dict:
        mttf = self.analysis["mttf_res"]
        items = [(name, row["mttf_days"]) for name, row in mttf.items() if np.isfinite(row["mttf_days"])]
        items = sorted(items, key=lambda item: item[1])[:15]
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.bar([name for name, _ in items], [value for _, value in items], color=self.tokens["secondary_slate_blue"], edgecolor="white")
        ax.set_title("Lowest Mean Time To Failure", fontsize=11, fontweight="bold")
        ax.set_ylabel("MTTF (days)")
        ax.tick_params(axis="x", rotation=60)
        self._apply_axes_style(ax)
        return self._save(fig, "mttf_days", "MTTF days ranking")

    def chart_start_stop(self) -> dict:
        start_stop = self.analysis["start_stop_df"].sort_index(key=lambda idx: [self.sort_key(item) for item in idx])
        fig, axes = plt.subplots(2, 1, figsize=(7.2, 8.4), constrained_layout=True)
        ax1, ax2 = axes
        start_abs = start_stop["start_dev"].abs()
        stop_abs = start_stop["stop_dev"].abs()
        worst_start = set(start_abs.nlargest(min(4, len(start_abs))).index)
        worst_stop = set(stop_abs.nlargest(min(4, len(stop_abs))).index)
        start_colors = [
            self.tokens["danger_red"] if name in worst_start else self.tokens["secondary_slate_blue"]
            for name in start_stop.index
        ]
        stop_colors = [
            self.tokens["danger_red"] if name in worst_stop else self.tokens["accent_orange"]
            for name in start_stop.index
        ]
        ax1.bar(start_stop.index, start_stop["start_dev"], color=start_colors, edgecolor="white")
        ax1.axhline(15, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax1.axhline(-15, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax1.set_title("Start Time Deviation", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Minutes vs fleet mean")
        ax1.tick_params(axis="x", rotation=55, labelsize=8.5)
        self._apply_axes_style(ax1)

        ax2.bar(start_stop.index, start_stop["stop_dev"], color=stop_colors, edgecolor="white")
        ax2.axhline(15, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax2.axhline(-15, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax2.set_title("Stop Time Deviation", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Minutes vs fleet mean")
        ax2.tick_params(axis="x", rotation=55, labelsize=8.5)
        self._apply_axes_style(ax2)
        return self._save(fig, "start_stop", "Start and stop deviation chart")

    def chart_clipping(self) -> dict:
        piv = self.analysis["piv"]
        irr = self.analysis["irr_data"]
        cap_kw = self.analysis["cap_kw"]
        site_pwr = piv.sum(axis=1, min_count=1)
        ghi_s = irr.set_index("ts")["GHI"].reindex(site_pwr.index)
        day = ghi_s > self.config["irr_threshold"]
        valid = day & site_pwr.notna() & ghi_s.notna()
        near_site = valid & (site_pwr >= 0.97 * cap_kw)
        fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.0), constrained_layout=True)
        ax1, ax2, ax3 = axes
        ax1.hist((site_pwr[valid] / cap_kw * 100).clip(0, 120), bins=np.arange(0, 121, 5), color=self.tokens["secondary_slate_blue"], edgecolor="white")
        ax1.axvline(97, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax1.set_title("Power Distribution", fontsize=10.5, fontweight="bold")
        ax1.set_xlabel("% of AC capacity")
        ax1.set_ylabel("Intervals")
        self._apply_axes_style(ax1)

        edges = [200, 400, 600, 800, 1000, 1300]
        labels = ["200-400", "400-600", "600-800", "800-1000", ">=1000"]
        frequencies = []
        for idx, label in enumerate(labels):
            lo = edges[idx]
            hi = edges[idx + 1]
            if idx < len(labels) - 1:
                mask = valid & (ghi_s >= lo) & (ghi_s < hi)
            else:
                mask = valid & (ghi_s >= 1000)
            frequencies.append(100.0 * (near_site & mask).sum() / max(mask.sum(), 1))
        ax2.bar(labels, frequencies, color=self.tokens["accent_orange"], edgecolor="white")
        ax2.set_title("Near-Clipping Frequency By Irradiance", fontsize=10.5, fontweight="bold")
        ax2.set_ylabel("Frequency (%)")
        self._apply_axes_style(ax2)

        inv_clip = {}
        for col in piv.columns:
            series = piv[col]
            mask = day & series.notna()
            inv_clip[col] = 100.0 * ((mask) & (series >= 0.97 * self.config["inv_ac_kw"])).sum() / max(mask.sum(), 1)
        top = sorted(inv_clip.items(), key=lambda item: item[1], reverse=True)[:12]
        ax3.bar([name for name, _ in top], [value for _, value in top], color=self.tokens["deep_indigo"], edgecolor="white")
        ax3.tick_params(axis="x", rotation=60)
        ax3.set_title("Top Inverters By Near-Clipping", fontsize=10.5, fontweight="bold")
        ax3.set_ylabel("Frequency (%)")
        self._apply_axes_style(ax3)
        return self._save(fig, "clipping", "Clipping diagnostics chart")

    def _load_curtailment_proxy_data(self):
        keys = ("curtail", "setpoint", "export", "limit", "dispatch")
        candidates = [path for path in self.config["data_dir"].glob("*.csv") if any(key in path.name.lower() for key in keys)]
        for path in candidates:
            try:
                df = pd.read_csv(path, sep=";", low_memory=False)
                cols = {col.lower().strip(): col for col in df.columns}
                time_col = next((cols[key] for key in ("time_utc", "time_udt", "timestamp", "datetime", "time", "ts") if key in cols), None)
                if time_col is None:
                    continue
                out = pd.DataFrame({"ts": pd.to_datetime(df[time_col], errors="coerce", dayfirst=True)})
                for col in df.columns:
                    if any(key in col.lower() for key in keys):
                        out[col] = pd.to_numeric(df[col], errors="coerce")
                out = out.dropna(subset=["ts"]).drop_duplicates(subset=["ts"]).set_index("ts").sort_index()
                if out.shape[1] > 0:
                    return path.name, out
            except Exception:
                continue
        return None, None

    def chart_curtailment(self) -> dict:
        piv = self.analysis["piv"]
        irr = self.analysis["irr_data"]
        site_pwr = piv.sum(axis=1, min_count=1)
        ghi_s = irr.set_index("ts")["GHI"].reindex(site_pwr.index)
        valid = (ghi_s > self.config["irr_threshold"]) & site_pwr.notna() & ghi_s.notna()
        near_clip = valid & (site_pwr >= 0.97 * self.config["cap_ac_kw"])
        potential = valid & (ghi_s >= 700) & site_pwr.between(0.80 * self.config["cap_ac_kw"], 0.97 * self.config["cap_ac_kw"])
        _, flags = self._load_curtailment_proxy_data()
        if flags is not None:
            aligned = flags.reindex(site_pwr.index).ffill()
            explicit = aligned.select_dtypes(include=[np.number]).notna().any(axis=1) & valid
        else:
            explicit = pd.Series(False, index=site_pwr.index)
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        ax.bar(
            ["Near clip", "Potential curtailment", "Explicit flag"],
            [
                100.0 * near_clip.sum() / max(valid.sum(), 1),
                100.0 * potential.sum() / max(valid.sum(), 1),
                100.0 * explicit.sum() / max(valid.sum(), 1),
            ],
            color=[self.tokens["warning_amber"], self.tokens["secondary_slate_blue"], self.tokens["primary_navy"]],
            edgecolor="white",
        )
        ax.set_title("Curtailment Signal Prevalence", fontsize=11, fontweight="bold")
        ax.set_ylabel("Share of daytime records (%)")
        self._apply_axes_style(ax)
        return self._save(fig, "curtailment", "Curtailment signal prevalence chart")

    def chart_degradation(self) -> dict:
        monthly = self.analysis["pr_res"]["monthly"][["PR"]].dropna().copy()
        monthly["year"] = monthly.index.year
        annual = monthly.groupby("year")["PR"].agg(["mean", "std", "count"]).reset_index()
        annual["ci95"] = 1.96 * annual["std"] / annual["count"].clip(lower=1).pow(0.5)
        fig, axes = self._figure("full", 2, 1)
        ax1, ax2 = axes
        ax1.errorbar(annual["year"], annual["mean"], yerr=annual["ci95"], fmt="o-", color=self.tokens["secondary_slate_blue"], ecolor=self.tokens["accent_orange"], capsize=4)
        if len(annual) >= 2:
            coeff = np.polyfit(annual["year"].astype(float), annual["mean"], 1)
            xx = np.linspace(float(annual["year"].min()), float(annual["year"].max()), 50)
            ax1.plot(xx, np.polyval(coeff, xx), linestyle="--", color=self.tokens["danger_red"], linewidth=1.1)
        ax1.set_title("Annual PR Trend With 95% Confidence Interval", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Annual PR (%)")
        self._apply_axes_style(ax1)

        rolling = monthly["PR"].rolling(6, min_periods=3).mean()
        ax2.plot(monthly.index, monthly["PR"], ".", color=self.tokens["secondary_slate_blue"], alpha=0.45, markersize=6)
        ax2.plot(rolling.index, rolling, color=self.tokens["danger_red"], linewidth=1.4)
        ax2.axhline(75, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax2.set_title("Monthly PR Stability", fontsize=11, fontweight="bold")
        ax2.set_ylabel("PR (%)")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax2)
        return self._save(fig, "degradation", "Degradation trend chart")

    def chart_peer_grouping(self) -> dict:
        piv = self.analysis["piv"]
        irr = self.analysis["irr_data"]
        pr_map = self.analysis["pr_res"]["per_inverter"]
        av_map = self.analysis["avail_res"]["per_inverter"]
        start_stop = self.analysis["start_stop_df"]
        site_day = irr.set_index("ts")["GHI"].reindex(piv.index) > self.config["irr_threshold"]
        rows = []
        for inv in piv.columns:
            day_series = piv[inv][site_day.reindex(piv.index).fillna(False)]
            mu = float(day_series.mean()) if len(day_series) else np.nan
            sd = float(day_series.std()) if len(day_series) else np.nan
            rows.append(
                {
                    "inv": inv,
                    "pr": float(pr_map.get(inv, np.nan)),
                    "av": float(av_map.get(inv, np.nan)),
                    "cv": sd / max(mu, 1e-6) if np.isfinite(mu) else np.nan,
                    "late": float(start_stop.loc[inv, "start_dev"]) if inv in start_stop.index else 0.0,
                }
            )
        df = pd.DataFrame(rows).dropna(subset=["pr", "av"])
        pr_thr = df["pr"].mean() - df["pr"].std()
        cv_thr = df["cv"].quantile(0.75)
        df["group"] = "Reference"
        df.loc[(df["pr"] < pr_thr) & (df["av"] >= 95), "group"] = "Low PR + High Av"
        df.loc[df["cv"] >= cv_thr, "group"] = "High Variability"
        df.loc[df["late"] > 5, "group"] = "Late-start Signature"
        palette = {
            "Reference": self.tokens["success_green"],
            "Low PR + High Av": self.tokens["danger_red"],
            "High Variability": self.tokens["warning_amber"],
            "Late-start Signature": self.tokens["secondary_slate_blue"],
        }
        fig, ax = self._figure("full")
        ax = ax if not isinstance(ax, np.ndarray) else ax[0]
        for group, subset in df.groupby("group"):
            ax.scatter(subset["av"], subset["pr"], label=f"{group} ({len(subset)})", s=44, alpha=0.85, color=palette.get(group, "#666666"))
        ax.axvline(95, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax.axhline(pr_thr, color=self.tokens["danger_red"], linestyle="--", linewidth=1.0)
        ax.legend(frameon=False, fontsize=8, loc="lower left")
        ax.set_title("Peer Grouping In PR vs Availability Space", fontsize=11, fontweight="bold")
        ax.set_xlabel("Availability (%)")
        ax.set_ylabel("PR (%)")
        self._apply_axes_style(ax)
        return self._save(fig, "peer_grouping", "Peer grouping scatter chart")

    def chart_timeline(self) -> dict:
        piv = self.analysis["piv"]
        irr = self.analysis["irr_data"]
        weather_data = self.analysis.get("weather_data")
        site_pwr = piv.sum(axis=1, min_count=1)
        ghi_s = irr.set_index("ts")["GHI"].reindex(site_pwr.index)
        day = ghi_s > self.config["irr_threshold"]
        daily_av = ((site_pwr > self.config["power_threshold"] * max(piv.shape[1], 1)) & day).resample("D").mean() * 100
        fig, axes = self._figure("full", 2, 1)
        ax1, ax2 = axes
        ax1.plot(daily_av.index, daily_av.values, color=self.tokens["secondary_slate_blue"], linewidth=1.1)
        outage_days = daily_av[daily_av < 80]
        if len(outage_days):
            ax1.scatter(outage_days.index, outage_days.values, color=self.tokens["danger_red"], s=18)
        ax1.axhline(95, color=self.tokens["success_green"], linestyle="--", linewidth=1.0)
        ax1.set_title("Outage Timeline", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Availability proxy (%)")
        self._apply_axes_style(ax1)

        if weather_data is not None:
            w_dates = pd.to_datetime(weather_data["daily"]["time"])
            w_rain = pd.Series(weather_data["daily"]["precipitation_sum"], index=w_dates, dtype="float64")
            w_temp = pd.Series(weather_data["daily"]["temperature_2m_max"], index=w_dates, dtype="float64")
            ax2.bar(w_rain.index, w_rain.values, width=1.0, color="#7DB6D8", alpha=0.55, label="Rain")
            hot_threshold = np.nanpercentile(w_temp.dropna(), 95) if w_temp.notna().any() else np.nan
            if np.isfinite(hot_threshold):
                hot = w_temp[w_temp >= hot_threshold]
                ax2.scatter(hot.index, np.repeat(max(w_rain.max(), 1) * 0.85, len(hot)), color=self.tokens["danger_red"], s=20, label="Temperature extreme")
            ax2.legend(frameon=False, fontsize=8, loc="upper left")
        else:
            ax2.text(0.02, 0.80, "Weather data unavailable for overlay.", transform=ax2.transAxes, color=self.tokens["muted_text"], fontsize=9)
        ax2.set_title("Weather Extremes Overlay", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Weather marker")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        self._apply_axes_style(ax2)
        return self._save(fig, "timeline", "Event timeline overlay chart")
