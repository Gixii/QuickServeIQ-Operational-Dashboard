import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------
# PAGE CONFIG
# -------------------------

st.set_page_config(
    page_title="QuickServeIQ",
    page_icon="📊",
    layout="wide"
)

# -------------------------
# LOAD DATA
# -------------------------

df = pd.read_csv("data/store_operations.csv")
# Ensure KPI exists (safety check)
if "labour_efficiency" not in df.columns:
    df["labour_efficiency"] = df["revenue"] / df["labour_cost"]

df["timestamp"] = pd.to_datetime(df["timestamp"])

df["hour"] = df["timestamp"].dt.hour
df["day_name"] = df["timestamp"].dt.day_name()

# -------------------------
# SIDEBAR FILTERS
# -------------------------

st.sidebar.header("Filters")

selected_days = st.sidebar.multiselect(
    "Select Days",
    options=sorted(df["day_name"].unique()),
    default=sorted(df["day_name"].unique())
)

hour_range = st.sidebar.slider(
    "Select Hour Range",
    0, 23, (0, 23)
)

# -------------------------
# APPLY FILTERS
# -------------------------

filtered_df = df[
    (df["day_name"].isin(selected_days)) &
    (df["hour"] >= hour_range[0]) &
    (df["hour"] <= hour_range[1])
]
# -------------------------
# KPI CALCULATIONS
# -------------------------

total_revenue = filtered_df["revenue"].sum()

total_customers = filtered_df["customers"].sum()
avg_wait_time = filtered_df["avg_wait_time"].mean()
avg_labour_efficiency = filtered_df["labour_efficiency"].mean()

avg_wait_time = 0 if pd.isna(avg_wait_time) else avg_wait_time
avg_labour_efficiency = 0 if pd.isna(avg_labour_efficiency) else avg_labour_efficiency

# -------------------------
# HEADER
# -------------------------

st.title("📊 QuickServeIQ")
st.subheader("Operational Intelligence Dashboard")

# -------------------------
# MANAGER SUMMARY
# -------------------------

st.header("📌 Manager Summary")

if len(filtered_df) > 0:
    peak_hour = (
        filtered_df.groupby("hour")["revenue"]
        .mean()
        .idxmax()
    )
else:
    peak_hour = "N/A"

if len(filtered_df) > 0:
    busiest_day = (
        filtered_df.groupby("day_name")["customers"]
        .mean()
        .idxmax()
    )
    st.info(f"Busiest day: {busiest_day}")

if peak_hour != "N/A":
    st.info(f"Peak revenue hour: {peak_hour}:00")
else:
    st.info("Peak revenue hour: N/A")
st.info(f"Average wait time: {avg_wait_time:.2f} minutes")
st.info(f"Labour efficiency: {avg_labour_efficiency:.2f}")

# -------------------------
# KPI CARDS
# -------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Revenue",
        f"£{total_revenue:,.0f}"
    )

with col2:
    st.metric(
        "Customers",
        f"{total_customers:,.0f}"
    )

with col3:
    st.metric(
        "Avg Wait Time",
        f"{avg_wait_time:.2f} min"
    )

with col4:
    st.metric(
        "Labour Efficiency",
        f"{avg_labour_efficiency:.2f}"
    )

st.divider()

# -------------------------
# SALES TREND
# -------------------------

hourly_sales = (
    filtered_df.groupby("hour")["revenue"]
    .mean()
    .reset_index()
)

sales_fig = px.line(
    hourly_sales,
    x="hour",
    y="revenue",
    title="Average Revenue by Hour",
    markers=True
)

st.plotly_chart(
    sales_fig,
    use_container_width=True
)

# -------------------------
# CUSTOMER TRAFFIC
# -------------------------

hourly_customers = (
    filtered_df.groupby("hour")["customers"]
    .mean()
    .reset_index()
)

customer_fig = px.bar(
    hourly_customers,
    x="hour",
    y="customers",
    title="Average Customer Traffic by Hour"
)

st.plotly_chart(
    customer_fig,
    use_container_width=True
)

# -------------------------
# LABOUR EFFICIENCY
# -------------------------

labour_efficiency = (
    filtered_df.groupby("hour")["labour_efficiency"]
    .mean()
    .reset_index()
)

efficiency_fig = px.line(
    labour_efficiency,
    x="hour",
    y="labour_efficiency",
    title="Labour Efficiency by Hour",
    markers=True
)

st.plotly_chart(
    efficiency_fig,
    use_container_width=True
)

# -------------------------
# FORECAST VS ACTUAL
# -------------------------

st.header("📊 Forecast vs Actual Sales")

forecast_df = (
    filtered_df.groupby("hour")[["revenue", "predicted_sales"]]
    .mean()
    .reset_index()
)

fig = px.line(
    forecast_df,
    x="hour",
    y=["revenue", "predicted_sales"],
    markers=True,
    title="Actual vs Predicted Sales"
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------
# OPERATIONS ALERTS
# -------------------------

st.header("⚠️ Operational Alerts")

if len(filtered_df) > 0 and filtered_df["avg_wait_time"].mean() > 4:
    st.warning("High wait times detected — consider increasing staffing during peak hours.")

if len(filtered_df) > 0 and filtered_df["labour_efficiency"].mean() < 6:
    st.error("Low labour efficiency — possible overstaffing or low demand periods.")

if len(filtered_df) > 0 and filtered_df["revenue"].mean() > 1000:
    st.success("Strong revenue performance across selected filters.")

# -------------------------
# RECOMMENDATIONS
# -------------------------

st.header("💡 Recommendations")

if len(filtered_df) > 0 and filtered_df["avg_wait_time"].mean() > 4 and filtered_df["customers"].mean() > 50:
    st.success("Increase staffing during peak hours (high demand + high wait times).")

elif len(filtered_df) > 0 and filtered_df["labour_efficiency"].mean() < 5:
    st.success("Review staffing allocation — potential overstaffing detected.")

else:
    st.success("Operations are within expected performance range.")