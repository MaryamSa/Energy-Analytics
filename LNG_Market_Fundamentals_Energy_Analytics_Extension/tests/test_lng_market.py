import pandas as pd
import pytest
from lng_market.model import reconcile_flows, run_scenarios, validate_baseline, market_note


def baseline():
    return pd.DataFrame([dict(month='2027-01', region='demo', domestic_supply_twh=10,
        pipeline_imports_twh=20, baseline_lng_imports_twh=15,
        baseline_demand_twh=50, storage_change_twh=-5,
        normal_hdd=100, forecast_hdd=100, twh_per_hdd=0.1)])


def test_central_balances_and_weather_sensitivity():
    df = run_scenarios(baseline())
    central = df.set_index('scenario').loc['central']
    assert central.required_lng_twh == pytest.approx(15)
    assert central.balance_at_baseline_lng_twh == pytest.approx(0)
    assert df.set_index('scenario').loc['cold', 'required_lng_twh'] > 15
    assert df.set_index('scenario').loc['mild', 'required_lng_twh'] < 15


def test_storage_injection_increases_required_imports():
    b = baseline()
    b.loc[0, 'storage_change_twh'] = 5
    assert run_scenarios(b).set_index('scenario').loc['central', 'required_lng_twh'] == pytest.approx(25)


def test_duplicate_and_negative_inputs_rejected():
    b = baseline()
    with pytest.raises(ValueError, match='Duplicate'):
        validate_baseline(pd.concat([b, b]))
    b.loc[0, 'forecast_hdd'] = -1
    with pytest.raises(ValueError, match='nonnegative'):
        run_scenarios(b)


def test_flow_checks_and_missing():
    f = pd.DataFrame([dict(month='2027-01', region='demo', origin='X', cargo_id='1', volume_twh=14)])
    c = reconcile_flows(f, baseline())
    assert c.loc[0, 'quality_flag'] == 'MISMATCH'
    assert 'SYNTHETIC' in market_note(run_scenarios(baseline()), c)
    assert reconcile_flows(f.iloc[0:0], baseline()).loc[0, 'quality_flag'] == 'MISSING'
    with pytest.raises(ValueError, match='Duplicate cargo'):
        reconcile_flows(pd.concat([f, f]), baseline())
