"""Configuration models and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Region:
    """A transparent latitude-longitude proxy for a power-market region."""

    key: str
    label: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def __post_init__(self) -> None:
        if not -90 <= self.lat_min < self.lat_max <= 90:
            raise ValueError(f"Invalid latitude bounds for {self.key}")
        if not -180 <= self.lon_min < self.lon_max <= 180:
            raise ValueError(f"Invalid longitude bounds for {self.key}")


def load_regions(path: Path) -> list[Region]:
    """Load and validate regional boxes from YAML."""

    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict) or not isinstance(content.get("regions"), dict):
        raise ValueError("Configuration must contain a 'regions' mapping")

    regions = []
    for key, values in content["regions"].items():
        regions.append(Region(key=key, **values))
    if not regions:
        raise ValueError("At least one region is required")
    return regions

