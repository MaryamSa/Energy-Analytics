# LNG Market Fundamentals: Weather-Sensitive European Gas Balance

**Portfolio extension for commodity-research roles.** This is a simplified, auditable **scenario and quality-control prototype**, not an operational gas trading model. All provided CSV values (including dates, origins, flows, demand, and sensitivities) are **synthetic illustrative assumptions**. They are not observations from ENTSOG, GIE, LNG terminals, or ECMWF, and no market inference should be drawn from their numerical magnitudes.

## Why this extension exists

The existing ECMWF project demonstrates skill in ensemble forecasting. LNG research additionally requires explicit accounting for **gas supply, pipeline imports, LNG arrivals, demand, storage injections/withdrawals, and import adequacy**. This extension provides a deliberately narrow, testable bridge: a monthly gas balance with transparent weather demand scenarios, a mock LNG cargo reconciliation and a written market note.

## What it does

1. Validates regional/monthly inputs, uniqueness, finite values and physical signs.
2. Calculates `weather_demand_delta_twh = (scenario_hdd - normal_hdd) × twh_per_hdd` using a clearly **uncalibrated** linear assumption.
3. Computes `LNG_required = max(0, demand + storage_injection - domestic_supply - pipeline_imports)` in TWh. Negative storage changes are withdrawals.
4. Compares required LNG with an assumed baseline of LNG imports and shows the balance/deficit if the baseline is held constant.
5. Aggregates illustrative per-cargo LNG receipts and flags `MISSING`/`MISMATCH` month-region entries; checks for duplicate cargo IDs.
6. Produces three CSV/Markdown outputs for analysts to review and explain.

**The mild/central/cold scenarios change forecast HDD by -15%/0/+15%. This is not a probabilistic forecast.** No regression model, capacity constraint, LNG price mechanism, or actual vessel-tracking system is asserted.

## Reproduce

From the repository root, with Python 3.11+ and the package dependencies already installed (`pip install -e ".[test]"`):

```bash
python -m lng_market --baseline examples/gas_baseline_demo.csv --flows examples/lng_flows_demo.csv --output lng_outputs
pytest -q tests/test_lng_market.py
```

Outputs:

- `lng_outputs/scenario_balances.csv`: all region-month-scenario balance calculations and weather demand sensitivities.
- `lng_outputs/flow_quality.csv`: cargo reconciliation differences and missing-source flags.
- `lng_outputs/market_note.md`: short, documented analyst-style scenario summary and limitations.

The example intentionally has **one LNG volume mismatch** (May) and **one missing flow month** (June) to exercise quality controls. Cargo IDs and origin labels are fabricated.

## How to connect this to the ECMWF project

The existing workflow produces regional 2m temperature outlooks. A *future* evidence-based integration could calculate country-specific heating degree days (HDD, e.g. `max(0, 18°C - daily_mean_temperature_C)`) using population-weighted temperature, and aggregate them to a region/month. This requires carefully aligned geography, calendar, valid times, ensemble members and a historical observed gas-demand series to estimate `twh_per_hdd`. **The demo HDD inputs here are not derived from ECMWF.** Avoid directly treating country boxes or ensemble means as demand-weighted temperature.

## A credible path to an operational version

- Connect appropriately licensed, time-stamped observations for European gas consumption, production, pipeline flows, LNG regasification receipts and storage injections/withdrawals; use source-specific units and convert to TWh with documented conventions.
- Calibrate weather–demand relationships by market and season, including day-of-week, holiday and structural-demand effects; use out-of-sample backtesting.
- Track shipments with unique vessel/cargo identifiers, timestamps, origin-destination mapping, revisions and confidence flags; reconcile against terminal receipts.
- Model contractual pipeline limits, regas capacity, storage withdrawal/injection limits, disruptions, and price/demand feedback; quantify uncertainty.
- Add versioned input snapshots, run timestamps, source attribution, and charts/research notes suitable for review by an analyst.

This module is standalone and does not modify or relabel the outputs of the ECMWF project.
## Add to an existing GitHub repository

Copy the directories `lng_market/`, `examples/`, `tests/test_lng_market.py`, `.github/workflows/lng-tests.yml` and this `README_LNG.md` into the **root** of `Energy-Analytics`. Keep the current ECMWF files unchanged. The supplied `lng_outputs/` directory is a generated illustrative example and may be omitted from your Git commit. Open a pull request to review the additions before merging. The separate GitHub Actions workflow tests this extension without downloading ECMWF datasets.
