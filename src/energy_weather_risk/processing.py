"""Scientific-data processing with explicit spatial weighting and units."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from .config import Region


def open_grib_field(path: Path) -> xr.DataArray:
    """Open a GRIB file that is expected to contain exactly one field."""

    dataset = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"indexpath": ""},
    )
    variables = list(dataset.data_vars)
    if len(variables) != 1:
        dataset.close()
        raise ValueError(f"Expected one data variable in {path}, found {variables}")
    return dataset[variables[0]]


def spatial_subset(field: xr.DataArray, region: Region) -> xr.DataArray:
    """Select a rectangular region, allowing ascending or descending latitude."""

    latitude = field["latitude"]
    lat_slice = (
        slice(region.lat_max, region.lat_min)
        if latitude[0] > latitude[-1]
        else slice(region.lat_min, region.lat_max)
    )
    subset = field.sel(
        latitude=lat_slice,
        longitude=slice(region.lon_min, region.lon_max),
    )
    if subset.sizes.get("latitude", 0) == 0 or subset.sizes.get("longitude", 0) == 0:
        raise ValueError(f"Region {region.key} does not overlap the data grid")
    return subset


def area_weighted_mean(field: xr.DataArray, region: Region) -> xr.DataArray:
    """Return a cosine-latitude-weighted mean over a regular lat-lon box."""

    subset = spatial_subset(field, region)
    weights = np.cos(np.deg2rad(subset["latitude"]))
    weights = xr.DataArray(
        weights,
        coords={"latitude": subset["latitude"]},
        dims=("latitude",),
    )
    return subset.weighted(weights).mean(("latitude", "longitude"))


def _field_frame(
    field: xr.DataArray,
    regions: list[Region],
    value_name: str,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for region in regions:
        series = area_weighted_mean(field, region)
        if "step" not in series.dims:
            series = series.expand_dims(step=[field.coords["step"].item()])
        frame = series.to_dataframe(name=value_name).reset_index()
        frame["region"] = region.key
        frame["region_label"] = region.label
        frames.append(frame[["region", "region_label", "valid_time", value_name]])
    return pd.concat(frames, ignore_index=True)


def build_regional_outlook(
    *,
    paths: dict[str, Path],
    regions: list[Region],
    run_start: datetime,
) -> pd.DataFrame:
    """Build regional energy-weather signals and run-to-run changes."""

    fields = {
        "temperature_mean_c": open_grib_field(paths["current_em_2t"]) - 273.15,
        "temperature_spread_k": open_grib_field(paths["current_es_2t"]),
        "wind100_mean_ms": open_grib_field(paths["current_em_100si"]),
        "wind100_spread_ms": open_grib_field(paths["current_es_100si"]),
        "previous_temperature_mean_c": open_grib_field(paths["previous_em_2t"])
        - 273.15,
        "previous_wind100_mean_ms": open_grib_field(paths["previous_em_100si"]),
    }

    merged: pd.DataFrame | None = None
    for name, field in fields.items():
        frame = _field_frame(field, regions, name)
        keys = ["region", "region_label", "valid_time"]
        merged = frame if merged is None else merged.merge(frame, how="left", on=keys)

    assert merged is not None
    merged["valid_time"] = pd.to_datetime(merged["valid_time"], utc=True)
    start = pd.Timestamp(run_start, tz="UTC")
    merged["lead_hours"] = (
        (merged["valid_time"] - start).dt.total_seconds() / 3600
    ).astype(int)
    merged["temperature_run_change_k"] = (
        merged["temperature_mean_c"] - merged["previous_temperature_mean_c"]
    )
    merged["wind100_run_change_ms"] = (
        merged["wind100_mean_ms"] - merged["previous_wind100_mean_ms"]
    )
    columns = [
        "region",
        "region_label",
        "valid_time",
        "lead_hours",
        "temperature_mean_c",
        "temperature_spread_k",
        "previous_temperature_mean_c",
        "temperature_run_change_k",
        "wind100_mean_ms",
        "wind100_spread_ms",
        "previous_wind100_mean_ms",
        "wind100_run_change_ms",
    ]
    region_order = {region.key: index for index, region in enumerate(regions)}
    merged["_region_order"] = merged["region"].map(region_order)
    return (
        merged.sort_values(["_region_order", "valid_time"])[columns]
        .reset_index(drop=True)
    )


def build_probability_outlook(
    *,
    paths: dict[str, Path],
    regions: list[Region],
) -> pd.DataFrame:
    """Aggregate ECMWF gridpoint event probabilities over each proxy region."""

    specifications = [
        (
            "precip_probability",
            "precip_ge_5mm_24h",
            "Area-mean gridpoint probability of ≥5 mm precipitation in 24 h",
        ),
        (
            "wind_probability",
            "wind10_ge_10ms",
            "Area-mean gridpoint probability of 10 m wind ≥10 m/s",
        ),
    ]
    frames: list[pd.DataFrame] = []
    for path_key, metric, label in specifications:
        field = open_grib_field(paths[path_key])
        frame = _field_frame(field, regions, "probability_pct")
        frame["metric"] = metric
        frame["metric_label"] = label
        frames.append(frame)

    result = pd.concat(frames, ignore_index=True)
    result["valid_time"] = pd.to_datetime(result["valid_time"], utc=True)
    if not result["probability_pct"].between(0, 100).all():
        raise ValueError("Probability values outside the expected 0-100% range")
    columns = [
        "region",
        "region_label",
        "valid_time",
        "metric",
        "metric_label",
        "probability_pct",
    ]
    region_order = {region.key: index for index, region in enumerate(regions)}
    result["_region_order"] = result["region"].map(region_order)
    return result.sort_values(["metric", "_region_order", "valid_time"])[columns]


def select_valid_time(field: xr.DataArray, valid_time: pd.Timestamp) -> xr.DataArray:
    """Select an exact valid time from a multi-step field."""

    target = np.datetime64(valid_time.tz_convert(None).to_datetime64())
    matches = np.flatnonzero(field["valid_time"].values == target)
    if len(matches) != 1:
        raise KeyError(f"Expected one field at {valid_time}, found {len(matches)}")
    return field.isel(step=int(matches[0]))
