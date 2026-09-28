"""Export reproducible V2 SQL and scenario summaries for a BI report."""
import csv
import sqlite3
from datetime import timedelta
from pathlib import Path

from engine import DB, run, test_start

OUT = Path(DB).parent / "bi_exports"
OUT.mkdir(parents=True, exist_ok=True)

def save(name, header, rows):
    with (OUT / name).open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

with sqlite3.connect(DB) as conn:
    load = conn.execute("""
        SELECT window_start, channel, sku, units, orders
        FROM kitchen_load_15m ORDER BY window_start, channel, sku
    """).fetchall()
    daily = conn.execute("""
        SELECT substr(window_start, 1, 10), channel, sku,
               SUM(units), SUM(orders)
        FROM kitchen_load_15m
        GROUP BY substr(window_start, 1, 10), channel, sku
        ORDER BY 1, 2, 3
    """).fetchall()
save("kitchen_load_15m.csv", ["window_start", "channel", "sku", "units", "orders"], load)
save("daily_item_channel.csv", ["date", "channel", "sku", "units", "orders_with_sku"], daily)

start = test_start - timedelta(days=20)
scenarios = []
for scenario in ("normal", "delivery_burst"):
    for fraction in (None, 0.5, 0.75, 1.0):
        x = run("forecast", start_day=start, days=20, horizon=15, buffer=0,
                max_batches=2, scenario=scenario,
                event_trigger=fraction is not None,
                trigger_fraction=fraction or 0.5)
        scenarios.append((scenario, "off" if fraction is None else fraction,
                          x["demand"], x["cooked"], x["wait_over_5"],
                          x["wait_over_10"], x["waste"], x["event_prompts"],
                          x["outstanding_at_cutoff"]))
save("policy_validation.csv",
     ["scenario", "queue_threshold_fraction", "demand_units", "cooked_units",
      "wait_over_5_units", "wait_over_10_units", "waste_units", "extra_prompts",
      "outstanding_at_cutoff"], scenarios)
print(f"Exported 3 files to {OUT}")
