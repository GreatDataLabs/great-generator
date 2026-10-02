# Hugging Face integration examples

These examples show how to use Great Generator alongside the Hugging Face ecosystem without making Hugging Face dependencies required for the base package.

## Install

```bash
pip install "great-generator[hf]"
pip install "great-generator[transformers]"
```

## Examples

| File | What it shows |
|---|---|
| `01_pandas_to_hf_dataset.ipynb` | Generate a pandas DataFrame and convert it to a Hugging Face `Dataset`. |
| `02_relational_to_hf_dataset_dict.ipynb` | Generate related tables and convert them to a `DatasetDict`. |
| `03_generate_dataset_card.py` | Generate a local Hugging Face-style dataset card Markdown file. |
| `04_transformers_advisor_schema_plan.ipynb` | Use a local Transformers model as a design-time advisor, then generate deterministic rows from the saved plan. |

These examples do not upload anything to the Hugging Face Hub by default and do not require a token for local conversion.
