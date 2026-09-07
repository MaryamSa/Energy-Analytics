"""Transparent clustering of IFS ensemble circulation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from .config import Region
from .processing import open_grib_field, spatial_subset


@dataclass(frozen=True)
class ScenarioClusters:
    """Cluster composites and an auditable member summary."""

    composites: xr.DataArray
    ensemble_mean: xr.DataArray
    summary: pd.DataFrame
    valid_time: pd.Timestamp
    retained_variance: float


def cluster_z500_scenarios(
    *,
    perturbed_path: Path,
    control_path: Path,
    n_clusters: int = 4,
    stride: int = 4,
    random_state: int = 42,
) -> ScenarioClusters:
    """Cluster ensemble-relative Z500 fields over the North Atlantic-Europe.

    This is scenario clustering, not a canonical weather-regime classifier:
    anomalies are relative to the current ensemble mean, not climatology.
    """

    domain = Region(
        key="north_atlantic_europe",
        label="North Atlantic-Europe",
        lat_min=30,
        lat_max=80,
        lon_min=-80,
        lon_max=40,
    )
    perturbed = spatial_subset(open_grib_field(perturbed_path), domain)
    control = spatial_subset(open_grib_field(control_path), domain)

    if "number" not in perturbed.dims:
        raise ValueError("Perturbed forecast file has no ensemble-member dimension")
    if "number" in control.dims:
        control = control.squeeze("number", drop=True)

    perturbed = perturbed.isel(
        latitude=slice(None, None, stride), longitude=slice(None, None, stride)
    ).load()
    control = control.isel(
        latitude=slice(None, None, stride), longitude=slice(None, None, stride)
    ).load()
    control = control.expand_dims(number=[0])
    field = xr.concat([control, perturbed], dim="number").sortby("number")
    if not 2 <= n_clusters < field.sizes["number"]:
        raise ValueError("n_clusters must be between 2 and the number of members - 1")

    ensemble_mean = field.mean("number")
    anomalies = field - ensemble_mean
    sqrt_weights = np.sqrt(np.cos(np.deg2rad(field["latitude"].values)))
    weighted = anomalies.values * sqrt_weights[None, :, None]
    matrix = weighted.reshape(field.sizes["number"], -1)

    components = min(10, matrix.shape[0] - 1, matrix.shape[1])
    pca = PCA(n_components=components, svd_solver="full")
    scores = pca.fit_transform(matrix)
    kmeans = KMeans(n_clusters=n_clusters, n_init=50, random_state=random_state)
    raw_labels = kmeans.fit_predict(scores)

    raw_counts = np.bincount(raw_labels, minlength=n_clusters)
    order = np.argsort(-raw_counts)
    relabel = {int(old): int(new) for new, old in enumerate(order, start=1)}
    labels = np.array([relabel[int(label)] for label in raw_labels])

    composites = []
    rows = []
    member_numbers = field["number"].values.astype(int)
    for label in range(1, n_clusters + 1):
        mask = labels == label
        cluster_field = anomalies.isel(number=np.flatnonzero(mask))
        composites.append(cluster_field.mean("number"))

        raw_label = next(raw for raw, new in relabel.items() if new == label)
        cluster_scores = scores[mask]
        distances = np.linalg.norm(cluster_scores - kmeans.cluster_centers_[raw_label], axis=1)
        representative_member = int(member_numbers[mask][np.argmin(distances)])
        count = int(mask.sum())
        rows.append(
            {
                "scenario": label,
                "member_count": count,
                "probability_pct": 100 * count / field.sizes["number"],
                "representative_member": representative_member,
            }
        )

    composite_array = xr.concat(composites, dim="scenario").assign_coords(
        scenario=np.arange(1, n_clusters + 1)
    )
    valid_time = pd.Timestamp(field["valid_time"].item(), tz="UTC")
    return ScenarioClusters(
        composites=composite_array,
        ensemble_mean=ensemble_mean,
        summary=pd.DataFrame(rows),
        valid_time=valid_time,
        retained_variance=float(pca.explained_variance_ratio_.sum()),
    )

