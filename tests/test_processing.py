import numpy as np
import pandas as pd
import pytest
import xarray as xr

from energy_weather_risk.config import Region
from energy_weather_risk.processing import area_weighted_mean, select_valid_time


def test_area_weighted_mean_uses_cosine_latitude() -> None:
    field = xr.DataArray(
        [[0.0, 0.0], [10.0, 10.0]],
        dims=("latitude", "longitude"),
        coords={"latitude": [60.0, 0.0], "longitude": [0.0, 1.0]},
    )
    region = Region("test", "Test", 0, 60, 0, 1)
    result = float(area_weighted_mean(field, region))
    expected = (0 * np.cos(np.deg2rad(60)) + 10 * np.cos(0)) / (
        np.cos(np.deg2rad(60)) + np.cos(0)
    )
    assert result == pytest.approx(expected)


def test_select_valid_time_returns_exact_step() -> None:
    times = pd.date_range("2026-01-01", periods=3, freq="6h")
    field = xr.DataArray(
        [1.0, 2.0, 3.0],
        dims=("step",),
        coords={"step": pd.to_timedelta([0, 6, 12], unit="h"), "valid_time": ("step", times)},
    )
    selected = select_valid_time(field, pd.Timestamp("2026-01-01 06:00", tz="UTC"))
    assert float(selected) == 2.0

