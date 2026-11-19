"""Transparent European gas balance and LNG scenario model.

Inputs are monthly quantities in TWh, NOT observed figures unless supplied by a user.
Positive storage_change_twh denotes injection (a source of demand), negative withdrawal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED = {
    'month', 'region', 'domestic_supply_twh', 'pipeline_imports_twh',
    'baseline_lng_imports_twh', 'baseline_demand_twh', 'storage_change_twh',
    'normal_hdd', 'forecast_hdd', 'twh_per_hdd',
}
SCENARIOS = {'mild': -0.15, 'central': 0.0, 'cold': 0.15}


def validate_baseline(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    x = df.copy()
    x['month'] = pd.to_datetime(x['month'], format='%Y-%m', errors='raise').dt.strftime('%Y-%m')
    if x[['month', 'region']].duplicated().any():
        raise ValueError('Duplicate month-region keys')
    nums = sorted(REQUIRED - {'month', 'region'})
    for col in nums:
        x[col] = pd.to_numeric(x[col], errors='raise')
    if not np.isfinite(x[nums].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite inputs')
    for col in ['domestic_supply_twh', 'pipeline_imports_twh', 'baseline_lng_imports_twh',
                'baseline_demand_twh', 'normal_hdd', 'forecast_hdd', 'twh_per_hdd']:
        if (x[col] < 0).any():
            raise ValueError(f'{col} must be nonnegative')
    return x.sort_values(['month', 'region']).reset_index(drop=True)


def run_scenarios(baseline: pd.DataFrame, scenario_spread: float = 0.15) -> pd.DataFrame:
    """Demand changes linearly with HDD relative to normal; not a calibrated forecast.

    Mild/cold vary forecast HDD by +/- scenario_spread. Unserved demand is the
    deficit if LNG stays at baseline. Required LNG is the balancing import level
    (clipped at zero); it is not a prediction of actual physical LNG deliveries.
    """
    if not (0 <= scenario_spread <= 1):
        raise ValueError('scenario_spread must lie between 0 and 1')
    x = validate_baseline(baseline)
    out = []
    for scenario, sign in [('mild', -1), ('central', 0), ('cold', 1)]:
        y = x.copy()
        y['scenario'] = scenario
        y['scenario_hdd'] = y['forecast_hdd'] * (1 + sign * scenario_spread)
        y['weather_demand_delta_twh'] = (y['scenario_hdd'] - y['normal_hdd']) * y['twh_per_hdd']
        y['scenario_demand_twh'] = y['baseline_demand_twh'] + y['weather_demand_delta_twh']
        if (y['scenario_demand_twh'] < 0).any():
            raise ValueError('Negative scenario demand; review HDD sensitivity')
        y['non_lng_supply_twh'] = y['domestic_supply_twh'] + y['pipeline_imports_twh']
        y['required_lng_twh'] = (y['scenario_demand_twh'] + y['storage_change_twh'] - y['non_lng_supply_twh']).clip(lower=0)
        y['incremental_lng_twh'] = y['required_lng_twh'] - y['baseline_lng_imports_twh']
        y['balance_at_baseline_lng_twh'] = (y['non_lng_supply_twh'] + y['baseline_lng_imports_twh']
                                            - y['scenario_demand_twh'] - y['storage_change_twh'])
        y['uncovered_deficit_twh'] = (-y['balance_at_baseline_lng_twh']).clip(lower=0)
        out.append(y)
    return pd.concat(out, ignore_index=True)


def reconcile_flows(flows: pd.DataFrame, baseline: pd.DataFrame, tolerance_twh: float = 0.01) -> pd.DataFrame:
    """Compare LNG arrivals by month/region against baseline; flag duplicates and gaps.

    Flow data must contain month, region, origin, cargo_id and volume_twh.
    Reconciliation highlights mismatches; it does not imply shipping tracking.
    """
    required = {'month', 'region', 'origin', 'cargo_id', 'volume_twh'}
    if required - set(flows):
        raise ValueError(f'Missing flow fields: {sorted(required - set(flows))}')
    f = flows.copy()
    f['month'] = pd.to_datetime(f['month'], format='%Y-%m', errors='raise').dt.strftime('%Y-%m')
    f['volume_twh'] = pd.to_numeric(f['volume_twh'], errors='raise')
    if (~np.isfinite(f['volume_twh'].to_numpy(dtype=float))).any() or (f['volume_twh'] < 0).any():
        raise ValueError('Flow volumes must be finite and nonnegative')
    if f[['month', 'region', 'cargo_id']].duplicated().any():
        raise ValueError('Duplicate cargo IDs within month-region; correct upstream records')
    totals = f.groupby(['month', 'region'], as_index=False)['volume_twh'].sum().rename(columns={'volume_twh': 'reported_lng_twh'})
    base = validate_baseline(baseline)[['month', 'region', 'baseline_lng_imports_twh']]
    if not f.empty and not set(map(tuple, f[['month', 'region']].to_numpy())).issubset(set(map(tuple, base[['month', 'region']].to_numpy()))):
        raise ValueError('Flow includes month-region not present in baseline')
    result = base.merge(totals, on=['month', 'region'], how='left')
    result['data_present'] = result['reported_lng_twh'].notna()
    result['reported_lng_twh'] = result['reported_lng_twh'].fillna(0.0)
    result['difference_twh'] = result['reported_lng_twh'] - result['baseline_lng_imports_twh']
    result['quality_flag'] = np.where(~result['data_present'], 'MISSING',
                             np.where(result['difference_twh'].abs() > tolerance_twh, 'MISMATCH', 'OK'))
    return result


def market_note(result: pd.DataFrame, checks: pd.DataFrame) -> str:
    """Generate a review-ready methodological summary rather than automated trading advice."""
    summary = result.groupby('scenario', sort=False).agg(
        required_lng_twh=('required_lng_twh', 'sum'),
        incremental_lng_twh=('incremental_lng_twh', 'sum'),
        uncovered_deficit_twh=('uncovered_deficit_twh', 'sum'),
    )
    months = sorted(result['month'].unique())
    lines = ['# European Gas Balance — Illustrative Scenario Note', '',
             f'**Period:** {months[0]} to {months[-1]}  ',
             '**Data status:** SYNTHETIC DEMONSTRATION — not historical, current or forecast market data.', '',
             '## Scenario summary (TWh)', '',
             '| Scenario | LNG required | Incremental LNG vs assumed baseline | Deficit at assumed LNG |',
             '|---|---:|---:|---:|']
    for scenario, row in summary.iterrows():
        lines.append(f"| {scenario} | {row.required_lng_twh:.1f} | {row.incremental_lng_twh:+.1f} | {row.uncovered_deficit_twh:.1f} |")
    issues = checks.loc[checks['quality_flag'] != 'OK']
    lines += ['', '## Data checks', '',
              f"{len(checks) - len(issues)} of {len(checks)} month-region reconciliations passed the illustrative LNG arrival check."]
    if not issues.empty:
        lines.append('Review the flagged periods in `flow_quality.csv`; mismatches are not proof of missing real-world shipments.')
    lines += ['', '## Interpretation and limitations', '',
              '- LNG required is the residual needed to balance a simplified monthly gas equation; it is **not** an LNG trade-flow or price forecast.',
              '- HDD demand sensitivity and all baseline values are assumptions, not calibrated estimates.',
              '- Real applications require observed gas demand, pipeline flows, LNG receipts, storage changes, capacity constraints, price response, and historical backtesting.',
              '- The weather scenario range is a sensitivity test, not a calibrated ensemble probability or confidence interval.',
              '- Positive storage change represents net injection; negative represents net withdrawal.', '']
    return '\n'.join(lines)
