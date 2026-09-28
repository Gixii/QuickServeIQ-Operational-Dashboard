"""Generate reproducible, fictional QuickServeIQ V2 order data."""
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "v2"
OUTPUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)
start = datetime(2026, 1, 1)
orders = []
items = []
order_id = 0

for day in range(90):
    date = start + timedelta(days=day)
    weekend = date.weekday() >= 5
    for hour in range(6, 22):
        for quarter in range(4):
            # Illustrative demand assumptions, not company operating data.
            expected = 2.0
            if 7 <= hour < 10:
                expected += 3.0
            if 12 <= hour < 14:
                expected += 4.0
            if 17 <= hour < 20:
                expected += 2.5
            if weekend:
                expected *= 1.2

            for _ in range(int(rng.poisson(expected))):
                order_id += 1
                placed_at = date.replace(hour=hour, minute=quarter * 15) + timedelta(
                    seconds=int(rng.integers(0, 900))
                )
                channel = str(rng.choice(
                    ["counter", "drive_thru", "delivery"], p=[0.42, 0.35, 0.23]
                ))
                delay = int(rng.integers(2, 9)) if channel == "delivery" else 0
                kitchen_at = placed_at + timedelta(minutes=delay)
                orders.append((order_id, placed_at.isoformat(sep=" "),
                               kitchen_at.isoformat(sep=" "), channel))

                menu = (["hash_brown", "breakfast_wrap"] if hour < 11 else
                        ["chicken_tenders", "fries"])
                for _ in range(int(rng.choice([1, 2], p=[0.72, 0.28]))):
                    sku = str(rng.choice(menu))
                    quantity = int(rng.choice([1, 2], p=[0.85, 0.15]))
                    items.append((order_id, sku, quantity))

def write_csv(name, header, rows):
    with (OUTPUT / name).open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

write_csv("orders.csv", ["order_id", "placed_at", "kitchen_at", "channel"], orders)
write_csv("order_items.csv", ["order_id", "sku", "quantity"], items)
print(f"Generated {len(orders):,} orders and {len(items):,} item lines in {OUTPUT}")
