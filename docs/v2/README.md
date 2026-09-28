# QuickServeIQ V2: kitchen decision replay

QuickServeIQ V2 simulates counter, drive-thru, and delivery orders reaching a quick-service kitchen. It compares 15-minute scheduled cooking checks with an optional queue-triggered batch. Its purpose is to make the trade-off between wait time and food waste inspectable. All orders and settings are fictional; this is not a Tim Hortons system or a measured deployment.

## Run on macOS

From the repository root, with the project virtual environment activated:

```bash
python scripts/v2/generate_orders.py
python scripts/v2/build_database.py
python scripts/v2/validate_v2.py
python scripts/v2/evaluate_policy.py
python scripts/v2/export_bi.py
python -m streamlit run dashboard/v2_app.py
```

V1 remains available with `python -m streamlit run dashboard/app.py`. V2 needs the `requirements.txt` packages. SQLite is part of Python's standard library.

## Data and method

| Component | Definition |
| --- | --- |
| `orders.csv` | Fictional order time, kitchen arrival time, and channel. Delivery kitchen arrival may follow placement. |
| `order_items.csv` | Item lines and quantities; duplicate item lines within one order are legitimate and summed. |
| `kitchen_load_15m` | SQL view of item units reaching the kitchen per 15-minute window and channel. |
| Forecast | Average of the same weekday and 15-minute slot in each of the previous four weeks. No actual future demand is read. |
| Scheduled check | Every 15 minutes, compare forecast plus backlog with ready and cooking units; start at most two batches per item. |
| Queue prompt | Optional: when waiting units reach a chosen fraction of a batch and nothing is cooking, start one extra batch. |
| Wait over 5 minutes | Count fulfilled units whose simulated wait exceeded five minutes, divided by total units demanded. Outstanding units, if any, appear separately. |
| Waste | Expired and end-of-replay ready units divided by all units cooked. |
| Closing | New simulated orders are placed before 22:00. Accepted orders can reach the kitchen shortly afterward. From 22:00 to 23:00, the engine cooks only enough batches to clear existing accepted orders. Any queue remaining at 23:00 is reported separately. |

The simulator rounds kitchen arrival to the minute and serves older waiting units first. Item preparation times, batch sizes and the 30-minute hold are scenario parameters in `scripts/v2/engine.py`, not verified restaurant settings. The 5-minute wait target and 20% waste budget are illustrative. There is no shared equipment-capacity constraint, item substitution, price model, or live point-of-sale integration.

## Scenarios and evaluation

The 90-day generated dataset has seeded demand patterns. The comparison period is February 26 to March 17, 2026. A delivery-burst scenario adds eight chicken-tender units at 12:05, 12:20, 12:35, and 12:50 every fifth validation day. Those added units are not in forecast history. In the dashboard, the burst applies to the selected replay date.

The final 14 days were inspected during development. They are **not** an untouched test set and should not be described as independent proof. Forecast errors and scenario outcomes are simulation results only. The generator deliberately creates breakfast and lunch peaks, so a peak-hour finding is not evidence about a real restaurant.

## BI export

`python scripts/v2/export_bi.py` creates:

- `data/v2/bi_exports/kitchen_load_15m.csv` for demand trends by time, channel and item.
- `data/v2/bi_exports/daily_item_channel.csv` for daily item/channel comparisons.
- `data/v2/bi_exports/policy_validation.csv` for scenario, queue-threshold, wait, waste and prompt comparisons.

These CSVs can be imported into Power BI Desktop on Windows. They are model outputs, not a finished `.pbix` report. When using `policy_validation.csv`, filter to one scenario and threshold or compare rows side by side; summing its scenario rows together would double-count demand.

See [powerbi_build_guide.md](powerbi_build_guide.md) for the report pages, field types, and measures.

## Portfolio claims

Describe V2 as a reproducible operational **simulation** with SQL demand aggregation, a historical baseline forecast, inventory replay, and an explainable cooking prompt. Do not claim a measured reduction in real store waiting time, waste, or labour cost.
