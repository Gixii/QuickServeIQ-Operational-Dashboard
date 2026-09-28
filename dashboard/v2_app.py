"""QuickServeIQ V2: transparent kitchen decision replay on synthetic data."""
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "v2"))
from engine import DB, MENU, run, test_start  # noqa: E402

st.set_page_config(page_title="QuickServeIQ V2", page_icon="🍳", layout="wide")
st.title("QuickServeIQ V2 | Kitchen Decision Replay")
st.caption("Fictional orders and illustrative cooking assumptions. This is a portfolio simulator, not a live store system.")

days = [test_start - timedelta(days=20-i) for i in range(20)]
with st.sidebar:
    st.header("Replay controls")
    day = st.selectbox("Date", days, index=3)
    burst = st.toggle("Unexpected delivery burst", value=False)
    trigger = st.toggle("Cook-now queue prompt", value=False)
    trigger_fraction = st.selectbox(
        "Queue threshold", [0.5, 0.75, 1.0],
        format_func=lambda v: {0.5: "Half a batch", 0.75: "Three quarters", 1.0: "Full batch"}[v],
        disabled=not trigger,
    )
    sku = st.selectbox("Item", list(MENU))
    st.caption("A burst adds 8 chicken-tender units at 12:05, 12:20, 12:35 and 12:50 on the selected day.")

scenario = "delivery_burst" if burst else "normal"
totals, breakdown, actions = run(
    "forecast", start_day=day, days=1, horizon=15, buffer=0,
    max_batches=2, scenario=scenario, event_trigger=trigger,
    trigger_fraction=trigger_fraction, detail=True
)
without = run("forecast", start_day=day, days=1, horizon=15,
              buffer=0, max_batches=2, scenario=scenario, event_trigger=False)

slow = totals["wait_over_5"]
slow_without = without["wait_over_5"]
slow_pct = slow / totals["demand"]
waste_pct = totals["waste"] / totals["cooked"]

a, b, c, d, e = st.columns(5)
a.metric("Kitchen demand", f"{totals['demand']:,} units")
b.metric("Waited over 5 min", f"{slow_pct:.1%}",
         delta=f"{(slow_without-slow)/totals['demand']:.1%} vs no trigger",
         delta_color="normal")
c.metric("Waited over 10 min", f"{totals['wait_over_10']/totals['demand']:.1%}")
d.metric("Waste / cooked", f"{waste_pct:.1%}")
e.metric("Extra queue prompts", totals["event_prompts"])
st.caption(f"Outstanding at 23:00 replay cutoff: {totals['outstanding_at_cutoff']} units. "
           "Accepted orders may be cooked after the 22:00 order cutoff.")
if waste_pct > .20:
    st.warning("Waste exceeds the illustrative 20% budget for this replay. "
               "Try a higher queue threshold or turn the extra prompt off.")

st.subheader("Decision trace")
item_actions = [x for x in actions if x["sku"] == sku and x["cook_units"] > 0]
if item_actions:
    labels = [f"{x['time']:%H:%M} | {x['reason']} | cook {x['cook_units']}" for x in item_actions]
    chosen = item_actions[st.selectbox("Choose a simulated prompt", range(len(labels)),
                                        format_func=lambda i: labels[i])]
    prep = MENU[sku]["prep_min"]
    st.info(f"Start {chosen['cook_units']} {sku.replace('_', ' ')} units at "
            f"{chosen['time']:%H:%M}. Estimated ready time: "
            f"{chosen['time'] + timedelta(minutes=prep):%H:%M}.")
    state = st.columns(4)
    state[0].metric("Ready before prompt", chosen["ready"])
    state[1].metric("Already cooking", chosen["cooking"])
    state[2].metric("Waiting in queue", chosen["backlog"])
    state[3].metric("Forecast", "—" if chosen["forecast"] is None
                    else f"{chosen['forecast']:.1f} / 15 min")
    st.caption(f"Reason: {chosen['reason']}. A cook-now queue prompt responds to visible backlog; "
               "it cannot remove the preparation delay for orders already waiting.")
else:
    st.info("No cook prompt for this item on the selected day.")

left, right = st.columns(2)
with left:
    st.subheader(f"{sku.replace('_', ' ').title()} by hour")
    hours = list(MENU[sku]["hours"])
    if breakdown[(sku, 22)]["demand"]:
        hours.append(22)
    hourly = pd.DataFrame([
        {"hour": h, "demand": breakdown[(sku, h)]["demand"],
         "waited_over_5m": breakdown[(sku, h)]["slow"]}
        for h in hours
    ])
    st.bar_chart(hourly.set_index("hour"), y=["demand", "waited_over_5m"])
with right:
    st.subheader("Orders reaching kitchen by channel")
    with sqlite3.connect(DB) as conn:
        channel_rows = conn.execute("""
            SELECT o.channel, SUM(i.quantity)
            FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
            WHERE substr(o.kitchen_at, 1, 10) = ?
            GROUP BY o.channel
        """, (str(day),)).fetchall()
    channel_units = dict(channel_rows)
    if burst:
        channel_units["delivery"] = channel_units.get("delivery", 0) + 32
    channel_df = pd.DataFrame(
        [{"channel": k, "units": v} for k, v in channel_units.items()]
    ).set_index("channel")
    st.bar_chart(channel_df)

with st.expander("Assumptions and limits"):
    st.write("The rule checks every 15 minutes, uses the average of the same slot in the prior "
             "four weeks, and starts at most two batches per item. When enabled, a queue "
             "reaching the selected threshold can prompt one extra batch if nothing is cooking.")
    st.write("All items use a 30-minute simulated holding limit. Menu batch sizes and preparation "
             "times are illustrative. The simulator has no shared kitchen-capacity constraint, "
             "and the five-minute service threshold and 20% waste budget are assumptions. "
             "The store stops accepting new orders at 22:00, but the replay continues to "
             "23:00 to finish accepted orders. Anything still queued at 23:00 is reported "
             "separately as outstanding at cutoff.")
    st.write("The delivery burst is injected at kitchen arrival. It is absent from forecast "
             "history and is shown separately from ordinary orders in the scenario logic.")
