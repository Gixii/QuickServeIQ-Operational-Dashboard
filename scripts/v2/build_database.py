"""Load generated V2 CSVs into SQLite and build analysis views."""
import csv
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "v2"
DB = DATA / "quickserveiq_v2.sqlite"
TEMP_DB = DATA / "quickserveiq_v2.building.sqlite"
VIEW_SQL = ROOT / "sql" / "v2" / "01_kitchen_load.sql"

TEMP_DB.unlink(missing_ok=True)
with closing(sqlite3.connect(TEMP_DB)) as conn:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        DROP VIEW IF EXISTS kitchen_load_15m;
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            placed_at TEXT NOT NULL,
            kitchen_at TEXT NOT NULL,
            channel TEXT NOT NULL CHECK (channel IN ('counter','drive_thru','delivery')),
            CHECK (kitchen_at >= placed_at)
        );
        CREATE TABLE order_items (
            line_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(order_id),
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0)
        );
        CREATE INDEX idx_orders_kitchen_at ON orders(kitchen_at);
        CREATE INDEX idx_items_order ON order_items(order_id);
    """)

    with (DATA / "orders.csv").open(newline="") as file:
        rows = csv.DictReader(file)
        conn.executemany(
            "INSERT INTO orders VALUES (:order_id, :placed_at, :kitchen_at, :channel)", rows
        )
    with (DATA / "order_items.csv").open(newline="") as file:
        rows = csv.DictReader(file)
        conn.executemany(
            "INSERT INTO order_items (order_id, sku, quantity) "
            "VALUES (:order_id, :sku, :quantity)", rows
        )
    conn.executescript(VIEW_SQL.read_text())

    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    item_lines = conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    raw_units = conn.execute("SELECT SUM(quantity) FROM order_items").fetchone()[0]
    view_units = conn.execute("SELECT SUM(units) FROM kitchen_load_15m").fetchone()[0]
    assert raw_units == view_units, (raw_units, view_units)
    print(f"Loaded {orders:,} orders and {item_lines:,} item lines; "
          f"{raw_units:,} units reconcile with the 15-minute view.")
    print("First five kitchen demand rows:")
    for row in conn.execute("SELECT window_start, channel, sku, units "
                            "FROM kitchen_load_15m ORDER BY window_start LIMIT 5"):
        print(row)
    conn.commit()
TEMP_DB.replace(DB)
