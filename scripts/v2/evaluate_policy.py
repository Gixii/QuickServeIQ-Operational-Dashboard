"""Compare queue thresholds after the corrected closing behavior."""
from datetime import timedelta

from engine import run, test_start

start = test_start - timedelta(days=20)
print(f"Simulated validation: {start} to {test_start - timedelta(days=1)}")
print("Scenario        Threshold  Wait >5m  Wait >10m  Waste/cooked  Prompts  Outstanding")
for scenario in ("normal", "delivery_burst"):
    for fraction in (None, 0.5, 0.75, 1.0):
        x = run("forecast", start_day=start, days=20, horizon=15, buffer=0,
                max_batches=2, scenario=scenario,
                event_trigger=fraction is not None,
                trigger_fraction=fraction or 0.5)
        label = "off" if fraction is None else str(fraction)
        print(f"{scenario:15s} {label:>9s} "
              f"{x['wait_over_5']/x['demand']:>9.1%} "
              f"{x['wait_over_10']/x['demand']:>10.1%} "
              f"{x['waste']/x['cooked']:>13.1%} "
              f"{x['event_prompts']:>8} {x['outstanding_at_cutoff']:>12}")
