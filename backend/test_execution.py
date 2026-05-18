# backend/test_execution.py

import json
from analytics_queries import (
    avg_late_days_query,
    pct_late_query,
    avg_abs_delay_query
)
from query_executor import execute_query
from chart_generator import generate_chart_spec


def run_query(label, sql):
    print(f"\n===== {label} =====\n")

    result = execute_query(sql)

    if "error" in result:
        print("Execution Error:")
        print(result["error"])
        return

    print("Row Count:", result["row_count"])
    print("\nFirst 5 Rows:")
    print(json.dumps(result["rows"][:5], indent=2))

    chart = generate_chart_spec(result)

    print("\nGenerated Chart Spec:")
    print(json.dumps(chart, indent=2))


if __name__ == "__main__":

    print("=== ANALYTICS TEST RUN ===")

    # 1️⃣ Average Late Days (only delayed orders)
    run_query(
        "Average Late Days (Late Orders Only)",
        avg_late_days_query()
    )

    # 2️⃣ Percentage of Late Orders
    run_query(
        "Percentage of Late Orders",
        pct_late_query()
    )

    # 3️⃣ Average Absolute Delay (magnitude regardless of early/late)
    run_query(
        "Average Absolute Delivery Delay",
        avg_abs_delay_query()
    )