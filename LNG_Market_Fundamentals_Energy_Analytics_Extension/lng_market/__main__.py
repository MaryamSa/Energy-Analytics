"""Run: python -m lng_market --baseline examples/gas_baseline_demo.csv --flows examples/lng_flows_demo.csv"""
import argparse
from pathlib import Path
import pandas as pd
from .model import market_note, reconcile_flows, run_scenarios


def main():
    parser = argparse.ArgumentParser(description='Illustrative gas/LNG balance analysis')
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--flows', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('lng_outputs'))
    args = parser.parse_args()
    result = run_scenarios(pd.read_csv(args.baseline))
    checks = reconcile_flows(pd.read_csv(args.flows), pd.read_csv(args.baseline))
    args.output.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output / 'scenario_balances.csv', index=False, float_format='%.4f')
    checks.to_csv(args.output / 'flow_quality.csv', index=False, float_format='%.4f')
    (args.output / 'market_note.md').write_text(market_note(result, checks), encoding='utf-8')
    print(f'Saved outputs to {args.output}')


if __name__ == '__main__':
    main()
