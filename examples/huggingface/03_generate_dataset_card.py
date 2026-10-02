from pathlib import Path

from great_generator import generate_hf_dataset_card

card = generate_hf_dataset_card(
    dataset_name="synthetic-retail-star-schema",
    domain="retail",
    row_counts={"dim_customer": 10000, "fact_sales": 1000000},
    generation_method="great-generator",
    synthetic=True,
    seed=42,
    intended_use=[
        "data engineering demos",
        "query testing",
        "analytics examples",
    ],
    not_intended_use=[
        "production analytics",
        "training models for real-world decision making",
        "privacy anonymization claims",
    ],
    limitations=[
        "Synthetic data only",
        "Does not represent real customers",
        "Does not reproduce production distributions unless configured",
    ],
    how_to_regenerate=(
        "Use Great Generator with the documented schema, row counts, generation settings, "
        "and seed. Review generated outputs before publishing any dataset artifact."
    ),
)

output = Path("synthetic-retail-star-schema-README.md")
output.write_text(card, encoding="utf-8")
print(f"Wrote {output}")
