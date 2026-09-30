# Snowflake examples

These examples prefer a file-based loading pattern:

1. Generate synthetic Parquet files locally or in a notebook runtime.
2. Upload or expose those files through a Snowflake stage configured by your platform team.
3. Load them with `COPY INTO`.

No credentials, private stages, or account-specific values are included.
