# Contract-to-Test examples

## Implemented

- `01_schema_to_test_dataset.ipynb`: schema + SQL -> deterministic relational witnesses,
  validation, coverage, and expected bounded outcomes.
- `schema_to_test_dataset.py`: script form of the same local workflow.

## Planned examples

The remaining master-roadmap notebooks will be added only when their underlying capability has
executable tests:

- pairwise/MC/DC predicate allocation;
- expanded relational and composite-key coverage;
- broader boundary and negative-case catalogs;
- full-query expected outputs;
- mutation-suite evaluation;
- Spark-native workload witnesses;
- temporal SCD2/fact/CDC validation;
- direct Unity Catalog contract compilation.

This avoids publishing notebooks that look runnable but contain unimplemented pseudocode.
