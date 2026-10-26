# Environment capture

Each benchmark result must record values detected at execution time:

- Great Generator version and Git commit, when available;
- Python and dependency versions;
- execution engine and engine version;
- operating system and architecture;
- CPU and memory limits for local runs;
- Spark/Databricks/Fabric/Snowflake runtime and compute configuration for platform runs;
- input contract, workload, generation-plan, and query-profile hashes;
- seed, row counts, partitions, format, compression, caching, and repetitions;
- measured timestamps and whether a result is measured or pending.

Templates must never contain placeholder hashes presented as measured values.
