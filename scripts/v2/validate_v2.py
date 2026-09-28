"""Check the data joins, replay accounting, and forecast isolation."""
import sqlite3
from datetime import timedelta

from engine import DB, run, test_start

with sqlite3.connect(DB) as conn:
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    raw_units = conn.execute("SELECT SUM(quantity) FROM order_items").fetchone()[0]
    grouped_units = conn.execute("SELECT SUM(units) FROM kitchen_load_15m").fetchone()[0]
    assert raw_units == grouped_units, (raw_units, grouped_units)
    bad_times = conn.execute("SELECT COUNT(*) FROM orders WHERE kitchen_at < placed_at").fetchone()[0]
    assert bad_times == 0

start = test_start - timedelta(days=20)
for scenario in ("normal", "delivery_burst"):
    for trigger in (False, True):
        x = run("forecast", start_day=start, days=20, horizon=15, buffer=0,
                max_batches=2, scenario=scenario, event_trigger=trigger)
        assert x["cooked"] == x["demand"] - x["outstanding_at_cutoff"] + x["waste"]
        assert x["outstanding_at_cutoff"] == 0, (scenario, trigger, x)
        assert x["wait_over_10"] <= x["wait_over_5"] <= x["delayed"] <= x["demand"]

# An unseen delivery burst must not alter the historical forecast at the same
# scheduled decision time (though it can change backlog and resulting actions).
_, _, normal_actions = run("forecast", start_day=start, days=1, horizon=15,
                           buffer=0, max_batches=2, detail=True)
_, _, burst_actions = run("forecast", start_day=start, days=1, horizon=15,
                          buffer=0, max_batches=2, scenario="delivery_burst", detail=True)
normal_forecasts = {(a["time"], a["sku"]): a["forecast"] for a in normal_actions
                    if a["reason"] == "Scheduled check"}
burst_forecasts = {(a["time"], a["sku"]): a["forecast"] for a in burst_actions
                   if a["reason"] == "Scheduled check"}
assert normal_forecasts == burst_forecasts
print(f"V2 checks passed: {raw_units:,} SQL units reconcile; no outstanding "
      "orders at replay cutoff; inventory balances; burst is excluded from forecast history.")
