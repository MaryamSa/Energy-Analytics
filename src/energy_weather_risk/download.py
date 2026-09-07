"""Resilient, explicit retrieval of the small ECMWF fields used here."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ecmwf.opendata import Client

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastRun:
    """A UTC model initialisation."""

    start: datetime

    @property
    def date(self) -> str:
        return self.start.strftime("%Y%m%d")

    @property
    def hour(self) -> int:
        return self.start.hour

    @property
    def tag(self) -> str:
        return self.start.strftime("%Y%m%d%H")


def _client(source: str, model: str) -> Client:
    return Client(
        source=source,
        model=model,
        infer_stream_keyword=False,
        maximum_retries=4,
        retry_after=5,
        use_server_retry_after=False,
    )


def latest_complete_run(source: str = "ecmwf", hour: int = 0) -> ForecastRun:
    """Return the latest run with both AIFS and IFS 10-day fields available."""

    aifs = _client(source, "aifs-ens")
    aifs_start = aifs.latest(
        time=hour,
        stream="enfo",
        type="em",
        step=240,
        param="2t",
    )
    ifs = _client(source, "ifs")
    ifs_start = ifs.latest(
        time=hour,
        stream="enfo",
        type="pf",
        step=240,
        param="gh",
        levelist=500,
        number=1,
    )
    return ForecastRun(start=min(aifs_start, ifs_start))


def retrieve_if_missing(
    *,
    client: Client,
    run: ForecastRun,
    target: Path,
    request: dict[str, Any],
) -> Path:
    """Download one validated request, reusing a non-empty local file."""

    if target.exists() and target.stat().st_size > 0:
        LOGGER.info("Reusing %s", target)
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    if temporary.exists():
        temporary.unlink()

    request = dict(request)
    stream = request.pop("stream", "enfo")
    LOGGER.info("Retrieving %s", target.name)
    client.retrieve(
        date=run.date,
        time=run.hour,
        stream=stream,
        target=str(temporary),
        **request,
    )
    if not temporary.exists() or temporary.stat().st_size == 0:
        raise RuntimeError(f"ECMWF returned an empty file for {target.name}")
    temporary.replace(target)
    return target


def retrieve_project_data(
    *,
    raw_dir: Path,
    run: ForecastRun,
    source: str = "ecmwf",
    max_step: int = 240,
    cluster_step: int = 240,
) -> dict[str, Path]:
    """Retrieve AIFS ENS summaries and one IFS ENS circulation snapshot."""

    if max_step % 6:
        raise ValueError("max_step must be divisible by 6")
    if cluster_step % 6:
        raise ValueError("cluster_step must be divisible by 6")

    steps = list(range(0, max_step + 1, 6))
    previous = ForecastRun(run.start - timedelta(days=1))
    paths: dict[str, Path] = {}
    aifs = _client(source, "aifs-ens")

    for data_type in ("em", "es"):
        for parameter in ("2t", "100si"):
            key = f"current_{data_type}_{parameter}"
            paths[key] = retrieve_if_missing(
                client=aifs,
                run=run,
                target=raw_dir / f"aifs_ens_{run.tag}_{data_type}_{parameter}.grib2",
                request={"type": data_type, "step": steps, "param": parameter},
            )

    for parameter in ("2t", "100si"):
        key = f"previous_em_{parameter}"
        paths[key] = retrieve_if_missing(
            client=aifs,
            run=previous,
            target=raw_dir / f"aifs_ens_{previous.tag}_em_{parameter}.grib2",
            request={"type": "em", "step": steps, "param": parameter},
        )

    daily_steps = [f"{start}-{start + 24}" for start in range(0, max_step, 24)]
    paths["precip_probability"] = retrieve_if_missing(
        client=aifs,
        run=run,
        target=raw_dir / f"aifs_ens_{run.tag}_ep_tpg5.grib2",
        request={"type": "ep", "step": daily_steps, "param": "tpg5"},
    )
    paths["wind_probability"] = retrieve_if_missing(
        client=aifs,
        run=run,
        target=raw_dir / f"aifs_ens_{run.tag}_ep_10spg10.grib2",
        request={
            "type": "ep",
            "step": list(range(12, max_step + 1, 12)),
            "param": "10spg10",
        },
    )

    ifs = _client(source, "ifs")
    paths["z500_perturbed"] = retrieve_if_missing(
        client=ifs,
        run=run,
        target=raw_dir / f"ifs_ens_{run.tag}_pf_gh500_step{cluster_step}.grib2",
        request={
            "type": "pf",
            "step": cluster_step,
            "param": "gh",
            "levelist": 500,
            "number": list(range(1, 51)),
        },
    )
    paths["z500_control"] = retrieve_if_missing(
        client=ifs,
        run=run,
        target=raw_dir / f"ifs_ens_{run.tag}_control_gh500_step{cluster_step}.grib2",
        request={
            # ECMWF Open Data publishes the IFS control under oper/fc.
            "stream": "oper",
            "type": "fc",
            "step": cluster_step,
            "param": "gh",
            "levelist": 500,
        },
    )
    return paths
