# Power BI report build guide

The V2 Python pipeline writes three CSV exports to `data/v2/bi_exports/`. Build the report in Power BI Desktop on Windows; the Mac workflow prepares and verifies the exports but does not create a `.pbix` file.

1. Run `python scripts/v2/export_bi.py` from the repository root.
2. In Power BI Desktop, use **Get data > Text/CSV** to load `kitchen_load_15m.csv` and `policy_validation.csv`. `daily_item_channel.csv` is optional for a separate daily view.
3. In Power Query, set `window_start` to Date/Time; keep `units` and `orders` as whole numbers. Keep `policy_validation` scenario and queue threshold as text/category fields; other counts are whole numbers.
4. Keep the demand and policy tables independent. The policy table is a scenario summary, not a dimension or a row-level fact table related to orders.

## Page 1: Kitchen demand

- Card: `Demand Units = SUM(kitchen_load_15m[units])`.
- Line or column chart: `window_start` on the axis, `Demand Units` as the value. A 15-minute or hourly view is useful.
- Stacked column chart: channel on legend, demand units by hour or date.
- Slicers: SKU, channel, date.
- Do not sum `orders` across SKUs as if it were unique store orders: an order containing two different items is present in two SKU groups.

## Page 2: Policy trade-off

Create these calculated columns in `policy_validation`:

```DAX
Wait Over 5 % = DIVIDE(policy_validation[wait_over_5_units], policy_validation[demand_units])
Wait Over 10 % = DIVIDE(policy_validation[wait_over_10_units], policy_validation[demand_units])
Waste % = DIVIDE(policy_validation[waste_units], policy_validation[cooked_units])
```

- Table: scenario, queue threshold, both wait percentages, waste percentage, extra prompts, outstanding at cutoff.
- Scatter chart: waste percentage on X, wait-over-five percentage on Y, threshold as details, scenario as legend, extra prompts as tooltip.
- Add a reference line at the **illustrative** 20% waste budget if helpful. The normal half-batch result is approximately 20.1%, so it is just above that line.

Do not add the scenario rows to a single grand-total demand card: the same base demand is replayed for each policy. Show each scenario/rule combination separately.

Label every page **Synthetic scenario analysis**. The report demonstrates SQL, modelling and trade-off communication; it does not measure outcomes at a real restaurant.
