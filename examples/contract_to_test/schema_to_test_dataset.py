"""Runnable contract-to-test example using only local Pandas data."""

from great_generator.testing import compile_test_dataset

TABLES = {
    "dim_customer": {
        "schema": "customer_id int primary key, region string not null",
        "rows": 30,
    },
    "fact_orders": {
        "schema": (
            "order_id int primary key, customer_id int references dim_customer.customer_id, "
            "order_status string not null, order_date date not null, amount double"
        ),
        "rows": 60,
    },
}

QUERY = """
SELECT c.region, COUNT(*) AS order_count
FROM fact_orders f
JOIN dim_customer c ON f.customer_id = c.customer_id
WHERE c.region = 'EAST'
  AND f.order_status = 'COMPLETED'
  AND f.order_date >= DATE '2026-01-01'
GROUP BY c.region
"""


def build_example():
    return compile_test_dataset(
        schema=TABLES,
        queries=[QUERY],
        coverage=["predicates", "joins", "boundaries"],
        seed=42,
    )


if __name__ == "__main__":
    result = build_example()
    print(result.coverage_report())
    print(result.datasets["fact_orders"].head())
