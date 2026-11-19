# European Gas Balance — Illustrative Scenario Note

**Period:** 2027-01 to 2027-06  
**Data status:** SYNTHETIC DEMONSTRATION — not historical, current or forecast market data.

## Scenario summary (TWh)

| Scenario | LNG required | Incremental LNG vs assumed baseline | Deficit at assumed LNG |
|---|---:|---:|---:|
| mild | 242.5 | -27.5 | 0.0 |
| central | 269.0 | -1.0 | 4.1 |
| cold | 295.5 | +25.5 | 25.6 |

## Data checks

4 of 6 month-region reconciliations passed the illustrative LNG arrival check.
Review the flagged periods in `flow_quality.csv`; mismatches are not proof of missing real-world shipments.

## Interpretation and limitations

- LNG required is the residual needed to balance a simplified monthly gas equation; it is **not** an LNG trade-flow or price forecast.
- HDD demand sensitivity and all baseline values are assumptions, not calibrated estimates.
- Real applications require observed gas demand, pipeline flows, LNG receipts, storage changes, capacity constraints, price response, and historical backtesting.
- The weather scenario range is a sensitivity test, not a calibrated ensemble probability or confidence interval.
- Positive storage change represents net injection; negative represents net withdrawal.
