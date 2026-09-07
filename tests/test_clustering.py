from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

import energy_weather_risk.clustering as clustering


def test_cluster_z500_scenarios_accounts_for_all_members(monkeypatch) -> None:
    latitude = np.linspace(80, 30, 11)
    longitude = np.linspace(-80, 40, 13)
    lon_pattern = np.sin(np.deg2rad(longitude))[None, :]
    lat_pattern = np.cos(np.deg2rad(latitude))[:, None]
    pattern = lon_pattern + lat_pattern
    base = 5500 + np.zeros_like(pattern)

    perturbed_values = np.stack(
        [base + sign * pattern * 40 + index for index, sign in enumerate([-1] * 4 + [1] * 4)]
    )
    perturbed = xr.DataArray(
        perturbed_values,
        dims=("number", "latitude", "longitude"),
        coords={
            "number": np.arange(1, 9),
            "latitude": latitude,
            "longitude": longitude,
            "valid_time": pd.Timestamp("2026-01-11").to_datetime64(),
        },
        name="gh",
    )
    control = xr.DataArray(
        base - pattern * 40,
        dims=("latitude", "longitude"),
        coords={
            "latitude": latitude,
            "longitude": longitude,
            "valid_time": pd.Timestamp("2026-01-11").to_datetime64(),
        },
        name="gh",
    )

    monkeypatch.setattr(
        clustering,
        "open_grib_field",
        lambda path: perturbed if Path(path).name == "perturbed" else control,
    )
    result = clustering.cluster_z500_scenarios(
        perturbed_path=Path("perturbed"),
        control_path=Path("control"),
        n_clusters=2,
        stride=1,
    )

    assert result.summary["member_count"].sum() == 9
    assert result.summary["probability_pct"].sum() == 100
    assert result.summary["member_count"].is_monotonic_decreasing
    assert result.composites.sizes["scenario"] == 2

