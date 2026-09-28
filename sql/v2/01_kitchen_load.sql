-- Demand reaches the kitchen at kitchen_at, not necessarily when placed.
-- Each selected item line contributes its quantity; repeated SKUs are summed.
CREATE VIEW kitchen_load_15m AS
SELECT
    strftime('%Y-%m-%d %H:', o.kitchen_at) ||
        printf('%02d:00', 15 * (CAST(strftime('%M', o.kitchen_at) AS INTEGER) / 15))
        AS window_start,
    o.channel,
    i.sku,
    SUM(i.quantity) AS units,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
GROUP BY window_start, o.channel, i.sku;
