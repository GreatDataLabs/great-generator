# Pandas and local examples

These notebooks run locally in Jupyter, Anaconda, VS Code, or any Python environment with `great-generator` installed.

| Notebook | Purpose |
|---|---|
| `01_generate_from_schema.ipynb` | Generate a Pandas DataFrame from a compact schema string. |
| `02_generate_from_json_schema.ipynb` | Generate from an API-style JSON Schema contract. |
| `03_generate_from_dbt_schema.ipynb` | Generate from dbt `schema.yml` metadata. |
| `04_generate_from_data_dictionary.ipynb` | Generate from a CSV/YAML/JSON data dictionary. |
| `05_relational_generation.ipynb` | Generate related tables and validate joins. |
| `06_query_aware_generation.ipynb` | Generate values and partitions needed by SQL tests. |
| `07_cdc_anomaly_generation.ipynb` | Generate CDC-style records and anomaly-rich synthetic data. |

Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records.
