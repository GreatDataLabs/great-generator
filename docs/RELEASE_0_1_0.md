# Great Generator v0.1.0 Release Notes

Great Generator v0.1.0 is the first public PyPI release of the project.

## Positioning

> Faker gives you fake values. Great Generator gives you a believable enterprise data system.

Great Generator is a developer-first Python library for generating realistic synthetic enterprise datasets for Pandas, Spark, lakehouse demos, testing, benchmarking, learning, teaching, dashboards, and research.

## Highlights

- Built-in enterprise domain packs including banking, ecommerce, healthcare, insurance, telecom, automotive, energy, manufacturing, logistics, media, public sector, hospitality, and SaaS.
- Relationship-aware generation with valid primary keys and foreign keys by default.
- Realistic value generation for names, emails, phones, addresses, merchants, products, providers, companies, statuses, account types, and other domain fields.
- Pandas and optional Spark generation engines.
- CSV, JSON, Parquet, and Delta export helpers.
- CDC-style banking customer change generation.
- Controlled anomaly injection for nulls, duplicates, orphan keys, late records, outliers, invalid statuses, negative amounts, and skew.
- Schema-first generation from compact schema strings, pandas DataFrames, PySpark StructTypes, and PySpark DataFrames.
- Custom relational schema generation for user-defined parent/child datasets.
- Deterministic generation with optional seeds.

## Install

```bash
pip install great-generator
```

Optional Spark and Delta extras:

```bash
pip install great-generator[spark]
pip install great-generator[delta]
```

## Quickstart

```python
from great_generator import generate_domain

data = generate_domain("banking", scale="small", realism="realistic", seed=42)

customers = data["customers"]
accounts = data["accounts"]
transactions = data["transactions"]
```

## Important note

Great Generator creates synthetic data from templates. It does not anonymize, de-identify, or transform real production data.

## Documentation

- README: https://github.com/GreatDataLabs/great-generator#readme
- Wiki: https://github.com/GreatDataLabs/great-generator/wiki
- PyPI release checklist: docs/PYPI_RELEASE.md
