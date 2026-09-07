"""Command-line pipeline for the ECMWF energy-weather portfolio project."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .clustering import cluster_z500_scenarios
from .config import load_regions
from .download import ForecastRun, latest_complete_run, retrieve_project_data
from .plotting import (
    plot_event_probabilities,
    plot_forecast_change_map,
    plot_regional_outlook,
    plot_scenario_clusters,
)
from .processing import build_probability_outlook, build_regional_outlook


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Retrieve ECMWF open data and build European energy-weather diagnostics."
    )
    parser.add_argument(
        "--date",
        help="Forecast initialisation date in YYYY-MM-DD; default is latest complete run.",
    )
    parser.add_argument("--hour", type=int, choices=(0, 12), default=0)
    parser.add_argument(
        "--source",
        choices=("ecmwf", "aws", "azure", "google"),
        default="ecmwf",
    )
    parser.add_argument("--max-step", type=int, default=240)
    parser.add_argument("--cluster-step", type=int, default=240)
    parser.add_argument("--clusters", type=int, default=4)
    parser.add_argument("--regions", type=Path, default=root / "config" / "regions.yml")
    parser.add_argument("--raw-dir", type=Path, default=root / "data" / "raw")
    parser.add_argument("--processed-dir", type=Path, default=root / "data" / "processed")
    parser.add_argument("--figures-dir", type=Path, default=root / "figures")
    return parser.parse_args()


def _resolve_run(args: argparse.Namespace) -> ForecastRun:
    if args.date:
        start = datetime.strptime(args.date, "%Y-%m-%d").replace(
            hour=args.hour, tzinfo=timezone.utc
        )
        return ForecastRun(start=start.replace(tzinfo=None))
    return latest_complete_run(source=args.source, hour=args.hour)


def run_pipeline(args: argparse.Namespace) -> dict[str, Path]:
    run = _resolve_run(args)
    regions = load_regions(args.regions)
    logging.info("Using forecast run %s UTC", run.start.isoformat())

    paths = retrieve_project_data(
        raw_dir=args.raw_dir,
        run=run,
        source=args.source,
        max_step=args.max_step,
        cluster_step=args.cluster_step,
    )
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    args.figures_dir.mkdir(parents=True, exist_ok=True)

    regional = build_regional_outlook(paths=paths, regions=regions, run_start=run.start)
    probabilities = build_probability_outlook(paths=paths, regions=regions)
    clusters = cluster_z500_scenarios(
        perturbed_path=paths["z500_perturbed"],
        control_path=paths["z500_control"],
        n_clusters=args.clusters,
    )

    outputs = {
        "regional_csv": args.processed_dir / "regional_outlook.csv",
        "probability_csv": args.processed_dir / "event_probabilities.csv",
        "cluster_csv": args.processed_dir / "cluster_summary.csv",
        "metadata_json": args.processed_dir / "run_metadata.json",
        "regional_plot": args.figures_dir / "regional_energy_outlook.png",
        "probability_plot": args.figures_dir / "energy_event_probabilities.png",
        "change_plot": args.figures_dir / "forecast_change_map.png",
        "cluster_plot": args.figures_dir / "z500_scenario_clusters.png",
    }
    regional.to_csv(outputs["regional_csv"], index=False, float_format="%.3f")
    probabilities.to_csv(outputs["probability_csv"], index=False, float_format="%.3f")
    clusters.summary.to_csv(outputs["cluster_csv"], index=False, float_format="%.3f")
    metadata = {
        "forecast_initialisation_utc": run.start.isoformat() + "Z",
        "forecast_horizon_hours": args.max_step,
        "circulation_cluster_lead_hours": args.cluster_step,
        "cluster_count": args.clusters,
        "pca_retained_variance_fraction": round(clusters.retained_variance, 6),
        "ecmwf_source": args.source,
        "models": ["AIFS ENS", "IFS ENS"],
        "regional_method": "cosine-latitude-weighted rectangular proxy regions",
    }
    outputs["metadata_json"].write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    plot_regional_outlook(regional, run_start=run.start, output=outputs["regional_plot"])
    plot_event_probabilities(
        probabilities, run_start=run.start, output=outputs["probability_plot"]
    )
    plot_forecast_change_map(
        paths=paths, run_start=run.start, output=outputs["change_plot"]
    )
    plot_scenario_clusters(clusters, run_start=run.start, output=outputs["cluster_plot"])
    return outputs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    outputs = run_pipeline(parse_args())
    print("\nCreated:")
    for path in outputs.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()

