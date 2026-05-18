
-- ANALYTICS VIEWS

SET search_path TO olist;


-- MATERIALIZED VIEW: ORDER REVENUE

-- Pre-computes total revenue per order
-- Improves performance for revenue queries

CREATE MATERIALIZED VIEW order_revenue AS
SELECT
    oi.order_id,
    SUM(oi.price + oi.freight_value) AS total_revenue
FROM order_items oi
GROUP BY oi.order_id;

CREATE INDEX idx_order_revenue_order
ON order_revenue(order_id);


-- VIEW: DELIVERY DELAY METRICS

-- Calculates delivery delay in days

CREATE VIEW order_delivery_metrics AS
SELECT
    order_id,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    EXTRACT(
        DAY FROM (order_delivered_customer_date - order_estimated_delivery_date)
    ) AS delivery_delay_days
FROM orders
WHERE order_delivered_customer_date IS NOT NULL;