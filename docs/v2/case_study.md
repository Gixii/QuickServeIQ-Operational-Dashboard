# QuickServeIQ V2 — portfolio case study

**Question:** Can a simple, explainable cooking prompt reduce simulated kitchen waits during demand bursts without producing too much waste?

**Scope:** A fictional quick-service kitchen. All orders, preparation times, batch sizes, holding limits and targets are synthetic or illustrative. This is a decision-support prototype, not a live restaurant deployment.

## Why this decision matters

A kitchen must start batches before they are needed because cooking takes time. Cooking too late creates a queue; cooking too early can leave ready food unused when its holding time expires. Delivery orders add another source of short-notice demand. A useful prompt therefore needs to show both the expected demand and the current kitchen state, and expose the resulting wait–waste trade-off.

## What I built

1. Generated 90 days of seeded orders across counter, drive-thru and delivery channels: **21,583 orders, 27,650 item lines and 31,836 units**. Duplicate item lines can occur within an order and are included in totals.
2. Loaded the CSVs into SQLite. A SQL view groups units by kitchen arrival, channel, item and 15-minute window; validation reconciles its total against the raw item lines.
3. Forecast each upcoming slot using the average of the same weekday and time over the previous four weeks. This is an interpretable baseline rather than a trained production model.
4. Replayed ready inventory, batches in progress, preparation time, first-in-first-out waiting orders and expiry. Scheduled checks run every 15 minutes. An optional queue rule starts one extra batch when waiting units reach a chosen fraction of a batch and nothing is already cooking.
5. Exposed the policy and its assumptions in a [Streamlit dashboard](https://quickserveiq-operational-dashboard-knyvzmxqbjwgvtueszs7pm.streamlit.app/), with item, date, burst and queue-threshold controls plus an individual cooking-decision trace.

## What the simulation showed

The comparison below covers **20 simulated days, February 26–March 17, 2026**, using a 15-minute forecast, no forecast buffer, and at most two batches per scheduled check. The burst adds eight chicken-tender units at four lunch times every fifth day and is excluded from forecast history.

| Scenario | Queue rule | Waited over 5 min / demand | Waste / cooked | Extra prompts |
| --- | --- | ---: | ---: | ---: |
| Normal | Off | 14.9% | 19.8% | 0 |
| Normal | Half a batch | 11.2% | 20.1% | 150 |
| Delivery burst | Off | 15.8% | 19.5% | 0 |
| Delivery burst | Half a batch | 11.9% | 19.8% | 160 |

The half-batch rule lowered simulated waits by **3.7 percentage points** in the normal scenario and **3.9 points** in the burst scenario. Waste rose by about **0.3 points** in both. In the normal scenario, 20.1% waste is **above** the illustrative 20% budget. The result supports exposing a threshold choice and a waste warning, not declaring one rule universally best.

A single-day walkthrough on **March 1, 2026** shows the delivery-burst scenario: with the queue rule off, **22.1%** of 435 units waited over five minutes; with the half-batch rule on, **16.8%** did, with **15.7%** waste/cooked and **eight** extra queue prompts. At 12:26, one simulated prompt sees four chicken-tender units waiting and starts six units estimated ready at 12:33. Already waiting orders cannot skip that preparation time.

## What this does and does not establish

The dashboard demonstrates a reproducible way to compare cooking rules and inspect their decisions. It does **not** establish a measured reduction in wait time or waste at a real store. Demand patterns are generated, operational settings are illustrative, and the final 14 days were inspected during development rather than held out as an untouched test. The engine does not model shared equipment capacity, labour availability, item substitution, actual discard practice or live point-of-sale events.

Before operational use, I would seek authorised, de-identified order-arrival and kitchen-ready timestamps plus waste records; validate item preparation and holding behaviour; add shared-capacity constraints; then compare policies on an untouched period and a supervised pilot. The five-minute wait target and 20% waste budget would need to be set by the operation.

**Explore:** [live dashboard](https://quickserveiq-operational-dashboard-knyvzmxqbjwgvtueszs7pm.streamlit.app/) · [method and metric definitions](README.md) · [Power BI export guide](powerbi_build_guide.md)
