"""Decision-oriented, publication-quality figures."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter

from .clustering import ScenarioClusters
from .config import Region
from .processing import open_grib_field, select_valid_time, spatial_subset

COLORS = {
    "navy": "#17324D",
    "blue": "#247BA0",
    "orange": "#F28E2B",
    "teal": "#2A9D8F",
    "red": "#D1495B",
    "grey": "#6B7280",
}
REGION_COLORS = [COLORS["blue"], COLORS["orange"], COLORS["teal"], COLORS["red"]]


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#9CA3AF",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#D1D5DB",
            "grid.alpha": 0.55,
            "figure.facecolor": "white",
        }
    )


def _date_axis(axis: plt.Axes) -> None:
    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    axis.xaxis.set_major_locator(locator)
    axis.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axis.grid(axis="y")


def plot_regional_outlook(
    frame: pd.DataFrame,
    *,
    run_start: datetime,
    output: Path,
) -> None:
    """Plot regional temperature and 100 m wind ensemble signals."""

    _apply_style()
    regions = frame[["region", "region_label"]].drop_duplicates().itertuples(index=False)
    region_rows = list(regions)
    fig, axes = plt.subplots(
        len(region_rows),
        2,
        figsize=(12.5, 3.15 * len(region_rows)),
        sharex=True,
        constrained_layout=False,
    )
    if len(region_rows) == 1:
        axes = np.array([axes])

    for row_index, row in enumerate(region_rows):
        data = frame.loc[frame["region"] == row.region].sort_values("valid_time")
        dates = data["valid_time"]

        temperature = axes[row_index, 0]
        lower_t = data["temperature_mean_c"] - data["temperature_spread_k"]
        upper_t = data["temperature_mean_c"] + data["temperature_spread_k"]
        temperature.fill_between(
            dates,
            lower_t,
            upper_t,
            color=COLORS["blue"],
            alpha=0.18,
            label="Mean gridpoint ensemble SD",
        )
        temperature.plot(
            dates,
            data["temperature_mean_c"],
            color=COLORS["blue"],
            linewidth=2.1,
            label="Current ensemble mean",
        )
        temperature.plot(
            dates,
            data["previous_temperature_mean_c"],
            color=COLORS["grey"],
            linewidth=1.5,
            linestyle="--",
            label="Previous 00 UTC run",
        )
        temperature.axhline(0, color="#9CA3AF", linewidth=0.8)
        temperature.set_ylabel("2 m temperature (deg C)")
        temperature.set_title(f"{row.region_label} | demand-relevant temperature")
        _date_axis(temperature)

        wind = axes[row_index, 1]
        lower_w = np.maximum(0, data["wind100_mean_ms"] - data["wind100_spread_ms"])
        upper_w = data["wind100_mean_ms"] + data["wind100_spread_ms"]
        wind.fill_between(
            dates,
            lower_w,
            upper_w,
            color=COLORS["teal"],
            alpha=0.2,
            label="Mean gridpoint ensemble SD",
        )
        wind.plot(
            dates,
            data["wind100_mean_ms"],
            color=COLORS["teal"],
            linewidth=2.1,
            label="Current ensemble mean",
        )
        wind.plot(
            dates,
            data["previous_wind100_mean_ms"],
            color=COLORS["grey"],
            linewidth=1.5,
            linestyle="--",
            label="Previous 00 UTC run",
        )
        wind.set_ylabel("100 m wind speed (m/s)")
        wind.set_title(f"{row.region_label} | wind-resource proxy")
        _date_axis(wind)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.925), frameon=False)
    fig.suptitle(
        "ECMWF AIFS ENS 10-day European energy-weather outlook",
        fontsize=17,
        fontweight="bold",
        color=COLORS["navy"],
        y=0.985,
    )
    fig.text(
        0.5,
        0.947,
        f"Initialised {run_start:%Y-%m-%d %H:%M} UTC | Area-weighted proxy-region means",
        ha="center",
        color=COLORS["grey"],
    )
    fig.text(
        0.01,
        0.008,
        "Shading uses the regional mean of pointwise ensemble SD; it is not the spread of the regional mean or a confidence interval. Weather signals are not load or power forecasts. Data: ECMWF Open Data (CC BY 4.0).",
        fontsize=8.2,
        color=COLORS["grey"],
    )
    fig.tight_layout(rect=(0.02, 0.035, 0.99, 0.91), h_pad=1.8, w_pad=1.4)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_event_probabilities(
    frame: pd.DataFrame,
    *,
    run_start: datetime,
    output: Path,
) -> None:
    """Plot transparent area-mean gridpoint event probabilities."""

    _apply_style()
    metrics = frame[["metric", "metric_label"]].drop_duplicates().itertuples(index=False)
    metric_rows = list(metrics)
    fig, axes = plt.subplots(len(metric_rows), 1, figsize=(11.5, 6.1), sharex=True)
    if len(metric_rows) == 1:
        axes = np.array([axes])

    for axis, metric in zip(axes, metric_rows, strict=True):
        data = frame.loc[frame["metric"] == metric.metric]
        for color, (region, region_frame) in zip(
            REGION_COLORS, data.groupby("region", sort=False), strict=False
        ):
            region_frame = region_frame.sort_values("valid_time")
            axis.plot(
                region_frame["valid_time"],
                region_frame["probability_pct"],
                marker="o",
                markersize=3.5,
                linewidth=1.9,
                color=color,
                label=region_frame["region_label"].iloc[0],
            )
        axis.set_title(metric.metric_label)
        axis.set_ylabel("Probability (%)")
        axis.set_ylim(0, 100)
        _date_axis(axis)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.875), frameon=False)
    fig.suptitle(
        "ECMWF AIFS ENS event probabilities",
        fontsize=17,
        fontweight="bold",
        color=COLORS["navy"],
        y=0.985,
    )
    fig.text(
        0.5,
        0.925,
        f"Initialised {run_start:%Y-%m-%d %H:%M} UTC",
        ha="center",
        color=COLORS["grey"],
    )
    fig.text(
        0.01,
        0.01,
        "Regional curves average gridpoint probabilities; they are not the probability that an entire region exceeds the threshold. Data: ECMWF Open Data (CC BY 4.0).",
        fontsize=8.2,
        color=COLORS["grey"],
    )
    fig.tight_layout(rect=(0.03, 0.055, 0.99, 0.81), h_pad=1.7)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _map_base(axis: plt.Axes, extent: list[float]) -> None:
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    axis.coastlines(resolution="110m", linewidth=0.65, color="#4B5563")
    axis.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.4, edgecolor="#6B7280")
    lon_span = extent[1] - extent[0]
    lat_span = extent[3] - extent[2]
    lon_step = 20 if lon_span > 70 else 10
    lat_step = 10
    lon_ticks = np.arange(
        np.ceil(extent[0] / lon_step) * lon_step, extent[1] + 0.1, lon_step
    )
    lat_ticks = np.arange(
        np.ceil(extent[2] / lat_step) * lat_step, extent[3] + 0.1, lat_step
    )
    axis.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
    axis.set_yticks(lat_ticks, crs=ccrs.PlateCarree())
    axis.xaxis.set_major_formatter(LongitudeFormatter())
    axis.yaxis.set_major_formatter(LatitudeFormatter())
    axis.tick_params(labelsize=8)
    axis.grid(linewidth=0.35, color="#9CA3AF", alpha=0.5, linestyle=":")


def plot_forecast_change_map(
    *,
    paths: dict[str, Path],
    run_start: datetime,
    output: Path,
    lead_hours: int = 168,
) -> None:
    """Map the ensemble mean, spread, and run-to-run change at one lead."""

    _apply_style()
    valid_time = pd.Timestamp(run_start, tz="UTC") + timedelta(hours=lead_hours)
    current = select_valid_time(open_grib_field(paths["current_em_2t"]), valid_time) - 273.15
    spread = select_valid_time(open_grib_field(paths["current_es_2t"]), valid_time)
    previous = select_valid_time(open_grib_field(paths["previous_em_2t"]), valid_time) - 273.15
    domain = Region("europe", "Europe", 35, 72, -15, 35)
    current = spatial_subset(current, domain).load()
    spread = spatial_subset(spread, domain).load()
    change = (current - spatial_subset(previous, domain)).load()

    transform = ccrs.PlateCarree()
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(15.5, 5.5),
        subplot_kw={"projection": transform},
    )
    specifications = [
        (current, "Ensemble mean 2 m temperature", "deg C", "coolwarm", None),
        (spread, "Ensemble spread (1 SD)", "K", "YlOrRd", 0),
        (change, "Change from previous 00 UTC run", "K", "RdBu_r", "symmetric"),
    ]
    for axis, (field, title, unit, cmap, mode) in zip(axes, specifications, strict=True):
        values = field.values[np.isfinite(field.values)]
        if mode == "symmetric":
            limit = max(0.5, float(np.nanpercentile(np.abs(values), 98)))
            levels = np.linspace(-limit, limit, 17)
        else:
            lower = float(np.nanpercentile(values, 2)) if mode is None else 0
            upper = float(np.nanpercentile(values, 98))
            if upper <= lower:
                upper = lower + 1
            levels = np.linspace(lower, upper, 17)
        image = axis.contourf(
            field["longitude"],
            field["latitude"],
            field,
            levels=levels,
            cmap=cmap,
            extend="both" if mode != 0 else "max",
            transform=transform,
        )
        _map_base(axis, [-15, 35, 35, 72])
        axis.set_title(title, pad=10)
        colorbar = fig.colorbar(
            image,
            ax=axis,
            orientation="horizontal",
            pad=0.08,
            shrink=0.88,
            format="%.1f",
        )
        colorbar.set_label(unit)

    fig.suptitle(
        f"Day-{lead_hours // 24} European temperature signal, uncertainty, and forecast change",
        fontsize=17,
        fontweight="bold",
        color=COLORS["navy"],
        y=1.01,
    )
    fig.text(
        0.5,
        0.945,
        f"ECMWF AIFS ENS | Initialised {run_start:%Y-%m-%d %H:%M} UTC | Valid {valid_time:%Y-%m-%d %H:%M} UTC",
        ha="center",
        color=COLORS["grey"],
    )
    fig.text(
        0.01,
        0.005,
        "Run-to-run change measures forecast evolution, not forecast error. Data: ECMWF Open Data (CC BY 4.0).",
        fontsize=8.2,
        color=COLORS["grey"],
    )
    fig.tight_layout(rect=(0.01, 0.03, 0.99, 0.92), w_pad=1.0)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_scenario_clusters(
    clusters: ScenarioClusters,
    *,
    run_start: datetime,
    output: Path,
) -> None:
    """Plot four ensemble-relative Z500 scenario composites."""

    _apply_style()
    transform = ccrs.PlateCarree()
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12.5, 7.5),
        subplot_kw={"projection": transform},
    )
    absolute = clusters.composites.values[np.isfinite(clusters.composites.values)]
    limit = max(10.0, float(np.nanpercentile(np.abs(absolute), 98)))
    levels = np.linspace(-limit, limit, 17)
    contour_levels = np.arange(4800, 6061, 60)

    image = None
    for axis, scenario in zip(axes.flat, clusters.summary.itertuples(index=False), strict=True):
        composite = clusters.composites.sel(scenario=scenario.scenario)
        image = axis.contourf(
            composite["longitude"],
            composite["latitude"],
            composite,
            levels=levels,
            cmap="RdBu_r",
            extend="both",
            transform=transform,
        )
        contours = axis.contour(
            clusters.ensemble_mean["longitude"],
            clusters.ensemble_mean["latitude"],
            clusters.ensemble_mean,
            levels=contour_levels,
            colors="#374151",
            linewidths=0.45,
            alpha=0.7,
            transform=transform,
        )
        axis.clabel(contours, inline=True, fontsize=6.5, fmt="%d")
        _map_base(axis, [-80, 40, 30, 80])
        axis.set_title(
            f"Scenario {scenario.scenario} | {scenario.probability_pct:.1f}% ({scenario.member_count}/51) | representative m{scenario.representative_member}",
            fontsize=10.2,
            pad=9,
        )

    assert image is not None
    colorbar_axis = fig.add_axes([0.28, 0.09, 0.44, 0.027])
    colorbar = fig.colorbar(image, cax=colorbar_axis, orientation="horizontal", format="%.1f")
    colorbar.set_label("Z500 anomaly relative to current ensemble mean (gpm)")
    fig.suptitle(
        "IFS ENS day-10 North Atlantic-European circulation scenarios",
        fontsize=17,
        fontweight="bold",
        color=COLORS["navy"],
        y=0.98,
    )
    fig.text(
        0.5,
        0.93,
        f"Initialised {run_start:%Y-%m-%d %H:%M} UTC | Valid {clusters.valid_time:%Y-%m-%d %H:%M} UTC | PCA + k-means (fixed k=4)",
        ha="center",
        color=COLORS["grey"],
    )
    fig.text(
        0.015,
        0.01,
        "Exploratory ensemble scenario clustering; anomalies are relative to this ensemble, not climatology, so these are not canonical weather regimes. Data: ECMWF Open Data (CC BY 4.0).",
        fontsize=8.2,
        color=COLORS["grey"],
    )
    fig.subplots_adjust(left=0.04, right=0.98, top=0.88, bottom=0.17, hspace=0.18, wspace=0.08)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)
