"""Replay two illustrative cooking rules on the final 14 synthetic days.

This is a scenario comparison, not an estimate of a real restaurant's results.
"""
import math
import sqlite3
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "v2" / "quickserveiq_v2.sqlite"

# Illustrative settings. Validate these with a real operation before any use.
MENU = {
    "hash_brown":      {"prep_min": 4, "hold_min": 30, "batch": 6, "hours": range(6, 11)},
    "breakfast_wrap":  {"prep_min": 6, "hold_min": 30, "batch": 4, "hours": range(6, 11)},
    "chicken_tenders": {"prep_min": 7, "hold_min": 30, "batch": 6, "hours": range(11, 22)},
    "fries":            {"prep_min": 4, "hold_min": 30, "batch": 6, "hours": range(11, 22)},
}

with sqlite3.connect(DB) as conn:
    historical = conn.execute("""
        SELECT window_start, sku, SUM(units)
        FROM kitchen_load_15m GROUP BY window_start, sku
    """).fetchall()
    event_rows = conn.execute("""
        SELECT o.kitchen_at, i.sku, SUM(i.quantity)
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        GROUP BY o.kitchen_at, i.sku ORDER BY o.kitchen_at
    """).fetchall()

demand_15 = {(datetime.fromisoformat(ts), sku): units
             for ts, sku, units in historical}
last_day = max(ts.date() for ts, _ in demand_15)
test_start = last_day - timedelta(days=13)
events = defaultdict(list)
for timestamp, sku, units in event_rows:
    moment = datetime.fromisoformat(timestamp).replace(second=0, microsecond=0)
    events[moment].append((sku, units))

def forecast_next(t, sku, horizon):
    # Upcoming 15-minute windows, averaged over the previous four weeks.
    return sum(
        demand_15.get((t - timedelta(weeks=w) + timedelta(minutes=m), sku), 0)
        for w in range(1, 5) for m in range(0, horizon, 15)
    ) / 4

def run(strategy, start_day=test_start, days=14, horizon=30, buffer=1,
        max_batches=2, detail=False, scenario="normal", event_trigger=False,
        trigger_fraction=0.5):
    if scenario not in ("normal", "delivery_burst"):
        raise ValueError(f"Unknown scenario: {scenario}")
    totals = defaultdict(int)
    by_sku_hour = defaultdict(lambda: defaultdict(int))
    actions = []
    for day_offset in range(days):
        day = start_day + timedelta(days=day_offset)
        ready = {sku: deque() for sku in MENU}  # [quantity, expiry]
        cooking = {sku: [] for sku in MENU}      # [quantity, ready_at]
        backlog = {sku: deque() for sku in MENU}  # [units, first_waiting_at]
        t = datetime(day.year, day.month, day.day, 6)
        end = t.replace(hour=23, minute=0)

        def serve(sku, units):
            """Consume oldest ready batches; return units still waiting."""
            while units and ready[sku]:
                batch = ready[sku][0]
                take = min(units, batch[0])
                batch[0] -= take
                units -= take
                if batch[0] == 0:
                    ready[sku].popleft()
            return units

        def serve_backlog(sku, now):
            while backlog[sku] and ready[sku]:
                entry = backlog[sku][0]
                remaining = serve(sku, entry[0])
                served = entry[0] - remaining
                wait = (now - entry[1]).total_seconds() / 60
                totals["wait_unit_minutes"] += served * wait
                if wait > 5:
                    totals["wait_over_5"] += served
                    by_sku_hour[(sku, entry[1].hour)]["slow"] += served
                if wait > 10:
                    totals["wait_over_10"] += served
                if remaining:
                    entry[0] = remaining
                else:
                    backlog[sku].popleft()

        while t <= end:
            for sku, cfg in MENU.items():
                while ready[sku] and ready[sku][0][1] <= t:
                    totals["waste"] += ready[sku].popleft()[0]
                for qty, ready_at in list(cooking[sku]):
                    if ready_at <= t:
                        cooking[sku].remove([qty, ready_at])
                        ready[sku].append([qty, ready_at + timedelta(minutes=cfg["hold_min"])])
                serve_backlog(sku, t)

            if t.hour < 22 and t.minute % 15 == 0:
                for sku, cfg in MENU.items():
                    if t.hour not in cfg["hours"]:
                        continue
                    on_hand = sum(batch[0] for batch in ready[sku])
                    in_progress = sum(batch[0] for batch in cooking[sku])
                    if strategy == "reactive":
                        batches = int(on_hand < 2 and in_progress == 0)
                        forecast = None
                    else:
                        pending = sum(entry[0] for entry in backlog[sku])
                        forecast = forecast_next(t, sku, horizon)
                        target = forecast + buffer + pending
                        needed = max(0, target - on_hand - in_progress)
                        batches = min(max_batches, math.ceil(needed / cfg["batch"]))
                    if detail and strategy != "reactive":
                        actions.append({
                            "time": t, "sku": sku, "reason": "Scheduled check",
                            "forecast": round(forecast, 2), "ready": on_hand,
                            "cooking": in_progress,
                            "backlog": sum(entry[0] for entry in backlog[sku]),
                            "cook_units": batches * cfg["batch"],
                        })
                    if batches:
                        qty = batches * cfg["batch"]
                        cooking[sku].append([qty, t + timedelta(minutes=cfg["prep_min"])])
                        totals["cooked"] += qty

            # After the simulated 22:00 order cutoff, finish accepted orders.
            # No new forecast stock is made; only the existing backlog is covered.
            if t.hour >= 22 and t < end:
                for sku, cfg in MENU.items():
                    pending = sum(entry[0] for entry in backlog[sku])
                    in_progress = sum(batch[0] for batch in cooking[sku])
                    needed = max(0, pending - in_progress)
                    if needed:
                        qty = math.ceil(needed / cfg["batch"]) * cfg["batch"]
                        cooking[sku].append([qty, t + timedelta(minutes=cfg["prep_min"])])
                        totals["cooked"] += qty
                        if detail:
                            actions.append({
                                "time": t, "sku": sku, "reason": "Finish accepted orders",
                                "forecast": None, "ready": 0, "cooking": in_progress,
                                "backlog": pending, "cook_units": qty,
                            })

            arrivals = list(events[t])
            # A deliberately unseen delivery cook-now surge on every fifth day.
            # These extra units never enter historical forecast data.
            if (scenario == "delivery_burst" and day_offset % 5 == 0
                    and t.hour == 12 and t.minute in (5, 20, 35, 50)):
                arrivals.append(("chicken_tenders", 8))
            for sku, units in arrivals:
                totals["demand"] += units
                by_sku_hour[(sku, t.hour)]["demand"] += units
                missing = serve(sku, units)
                totals["delayed"] += missing
                if missing:
                    backlog[sku].append([missing, t])
                    # A cook-now prompt can respond to an unexpected queue.
                    # It cannot make food ready sooner than prep_min.
                    pending = sum(entry[0] for entry in backlog[sku])
                    cfg = MENU[sku]
                    if (event_trigger and t.hour in cfg["hours"]
                            and pending >= math.ceil(cfg["batch"] * trigger_fraction)
                            and not cooking[sku]):
                        cooking[sku].append([cfg["batch"],
                                             t + timedelta(minutes=cfg["prep_min"])])
                        totals["cooked"] += cfg["batch"]
                        totals["event_prompts"] += 1
                        if detail:
                            actions.append({
                                "time": t, "sku": sku, "reason": "Cook-now queue",
                                "forecast": None, "ready": 0, "cooking": 0,
                                "backlog": pending, "cook_units": cfg["batch"],
                            })
            t += timedelta(minutes=1)

        for sku, queue in backlog.items():
            for units, since in queue:
                totals["outstanding_at_cutoff"] += units
                by_sku_hour[(sku, since.hour)]["outstanding"] += units
        totals["waste"] += sum(batch[0] for batches in ready.values() for batch in batches)
    assert totals["cooked"] == (totals["demand"] - totals["outstanding_at_cutoff"]
                                + totals["waste"]), "Inventory does not reconcile"
    if detail:
        return totals, by_sku_hour, actions
    return totals

if __name__ == "__main__":
    print(f"Scenario replay: {test_start} to {last_day}; 15-minute decisions, 30-minute forecast")
    print("Assumptions: 30-minute hold; batch sizes/prep times in MENU; one-unit forecast buffer.")
    print("Delayed = units unavailable when an order reaches the kitchen; they enter a backlog.")
    for strategy in ("reactive", "forecast"):
        x = run(strategy)
        print(f"{strategy:8s} | demand {x['demand']:5d} | cooked {x['cooked']:5d} | "
              f"delayed {x['delayed']:5d} ({x['delayed']/x['demand']:.1%}) | "
              f"waste {x['waste']:5d} ({x['waste']/x['cooked']:.1%}) | "
              f"outstanding at replay cutoff {x['outstanding_at_cutoff']}")
