# backend/analytics_queries.py

def avg_late_days_query():
    return """
    SELECT
        c.customer_state,
        AVG(odm.delivery_delay_days) AS avg_late_days
    FROM order_delivery_metrics odm
    JOIN orders o ON odm.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE odm.delivery_delay_days > 0
    GROUP BY c.customer_state
    ORDER BY avg_late_days DESC;
    """


def pct_late_query():
    return """
    SELECT
        c.customer_state,
        COUNT(*) FILTER (WHERE odm.delivery_delay_days > 0) AS late_count,
        COUNT(*) AS total_orders,
        (COUNT(*) FILTER (WHERE odm.delivery_delay_days > 0)::float / COUNT(*)) * 100 AS pct_late
    FROM order_delivery_metrics odm
    JOIN orders o ON odm.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state
    ORDER BY pct_late DESC;
    """


def avg_abs_delay_query():
    return """
    SELECT
        c.customer_state,
        AVG(ABS(odm.delivery_delay_days)) AS avg_abs_delay
    FROM order_delivery_metrics odm
    JOIN orders o ON odm.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state
    ORDER BY avg_abs_delay DESC;
    """