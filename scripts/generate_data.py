import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# -----------------------------
# CONFIG
# -----------------------------

start_date = datetime(2026, 1, 1)
hours = 24 * 90  # 90 days of hourly data

timestamps = [start_date + timedelta(hours=i) for i in range(hours)]

data = []

# -----------------------------
# DATA GENERATION
# -----------------------------

for ts in timestamps:

    hour = ts.hour
    day = ts.weekday()  # 0 = Monday, 6 = Sunday

    # -----------------------------
    # BASE CUSTOMER TRAFFIC
    # -----------------------------

    customers = 15

    # Breakfast rush
    if 7 <= hour <= 10:
        customers += 45

    # Lunch rush
    if 11 <= hour <= 14:
        customers += 65

    # Afternoon moderate traffic
    if 15 <= hour <= 17:
        customers += 25

    # Evening slowdown
    if hour >= 20:
        customers -= 10

    # Very late night
    if 0 <= hour <= 5:
        customers -= 8

    # Weekend boost
    if day >= 5:
        customers += 20

    # -----------------------------
    # RANDOM STORE VARIATION
    # -----------------------------

    # Random quieter periods
    if np.random.random() < 0.05:
        customers *= 0.7

    # Random busy spikes
    if np.random.random() < 0.03:
        customers *= 1.3

    # Random noise
    customers += np.random.randint(-5, 8)

    customers = int(max(customers, 5))

    # -----------------------------
    # TRANSACTIONS
    # -----------------------------

    transactions = int(customers * np.random.uniform(0.75, 1.0))

    transactions = max(transactions, 1)

    # -----------------------------
    # AVERAGE ORDER VALUE
    # -----------------------------

    avg_order_value = np.random.uniform(6, 11)

    # Breakfast coffee boost
    if 7 <= hour <= 9:
        avg_order_value += 1.5

    # Lunch meal boost
    if 11 <= hour <= 14:
        avg_order_value += 2

    # -----------------------------
    # REVENUE
    # -----------------------------

    revenue = transactions * avg_order_value

    # Random sales fluctuation
    revenue *= np.random.uniform(0.92, 1.08)

    # -----------------------------
    # PREDICTED SALES
    # -----------------------------

    predicted_sales = revenue * np.random.uniform(0.9, 1.1)

    # -----------------------------
    # STAFFING LOGIC
    # -----------------------------

    if customers < 20:
        staff_count = 2

    elif customers < 40:
        staff_count = 3

    elif customers < 70:
        staff_count = 5

    else:
        staff_count = 7

    # Weekend staffing
    if day >= 5:
        staff_count += 1

    # -----------------------------
    # LABOUR COST
    # -----------------------------

    hourly_wage = np.random.uniform(12, 15)

    labour_cost = staff_count * hourly_wage

    # Simulate inefficiency
    if customers < 25 and staff_count > 4:
        labour_cost *= 1.2

    # -----------------------------
    # WAIT TIMES
    # -----------------------------

    avg_wait_time = np.random.uniform(2, 4)

    if customers > 60:
        avg_wait_time += np.random.uniform(1, 3)

    # -----------------------------
    # DRIVE THRU TIME
    # -----------------------------

    drive_thru_time = np.random.uniform(3, 6)

    if customers > 70:
        drive_thru_time += np.random.uniform(1, 2)

    # -----------------------------
    # APPEND ROW
    # -----------------------------

    data.append([
        ts,
        customers,
        round(revenue, 2),
        transactions,
        round(avg_order_value, 2),
        round(predicted_sales, 2),
        round(labour_cost, 2),
        staff_count,
        round(avg_wait_time, 2),
        round(drive_thru_time, 2)
    ])

# -----------------------------
# CREATE DATAFRAME
# -----------------------------

df = pd.DataFrame(data, columns=[
    "timestamp",
    "customers",
    "revenue",
    "transactions",
    "avg_order_value",
    "predicted_sales",
    "labour_cost",
    "staff_count",
    "avg_wait_time",
    "drive_thru_time"
])

# -----------------------------
# EXTRA KPI CALCULATIONS
# -----------------------------

df["labour_efficiency"] = (
    df["revenue"] / df["labour_cost"]
).round(2)

df["sales_vs_prediction_diff"] = (
    df["revenue"] - df["predicted_sales"]
).round(2)

# -----------------------------
# SAVE DATA
# -----------------------------

df.to_csv("data/store_operations.csv", index=False)

print("Dataset generated successfully!")
print(df.head())