# European Gas Market Analysis

## About this project

I started this extension to explore how weather conditions can affect natural gas demand in Europe.

My original project focuses on ECMWF weather forecasts and forecast uncertainty. Here, I wanted to explore how temperature changes could affect gas demand and the amount of LNG needed to balance supply and demand.

For now, the project uses a simple monthly gas balance model and three weather scenarios.

## Questions I wanted to explore

1. How does colder or milder weather affect estimated gas demand?
2. How much LNG is needed after accounting for domestic production, pipeline imports and storage changes?
3. How can data checks identify inconsistent LNG import records?

## How the model works

The model starts with monthly gas demand, domestic production, pipeline imports and storage changes.

It calculates the remaining gas requirement that would need to be met through LNG imports.

The model then compares three scenarios:

- **Mild:** Heating degree days are 15% below the central scenario.
- **Central:** The original assumed weather conditions.
- **Cold:** Heating degree days are 15% above the central scenario.

Heating degree days (HDD) provide a simple indication of heating needs. The model assumes a linear relationship between changes in HDD and gas demand.

This relationship has not yet been calibrated against observed gas consumption.

## Example results

Using synthetic data for January–June 2027, the model produces:

| Scenario | LNG requirement (TWh) |
|---|---:|
| Mild | 242.5 |
| Central | 269.0 |
| Cold | 295.5 |

In this example, colder conditions increase estimated demand and therefore increase the amount of LNG needed to balance the system.

These are illustrative calculations, not actual European gas-market forecasts.

## LNG data checks

I also added a data-validation step that compares the LNG import volumes in the example cargo records with the assumed monthly import totals.

The dataset deliberately contains one mismatched month and one missing month to check whether the program identifies these problems.

## Running the analysis

Install the project from the repository root:

```bash
python -m pip install -e ".[test]"
```

Run the example:

```bash
python -m lng_market --baseline examples/gas_baseline_demo.csv --flows examples/lng_flows_demo.csv --output lng_outputs
```

Run the tests:

```bash
python -m pytest -q
```

The generated files are saved in `lng_outputs/`.

## Limitations and next steps

This is an exploratory model using synthetic data.

The relationship between weather and demand has not been estimated from observations. The model also does not account for LNG prices, import capacity or other operational constraints.

The HDD values are not yet derived from ECMWF weather forecasts.

My next steps are to work with historical European gas data, estimate how temperature affects consumption, and explore how to connect this analysis with the existing ECMWF forecasting workflow.
