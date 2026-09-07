from pathlib import Path

import pytest

from energy_weather_risk.config import Region, load_regions


def test_region_rejects_reversed_latitudes() -> None:
    with pytest.raises(ValueError, match="latitude"):
        Region("bad", "Bad", 60, 50, 0, 10)


def test_load_regions_reads_named_mapping(tmp_path: Path) -> None:
    path = tmp_path / "regions.yml"
    path.write_text(
        """regions:
  test:
    label: Test region
    lat_min: 40
    lat_max: 50
    lon_min: 0
    lon_max: 10
""",
        encoding="utf-8",
    )
    assert load_regions(path) == [Region("test", "Test region", 40, 50, 0, 10)]

