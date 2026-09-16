"""Public API surface."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from great_generator.cdc.generator import generate_cdc as _generate_cdc
from great_generator.config import resolve_row_counts
from great_generator.core.realism import normalize_realism_mode, validate_realism
from great_generator.domains import DOMAIN_MODULES
from great_generator.exporters.csv_exporter import export_csv
from great_generator.exporters.delta_exporter import export_delta
from great_generator.exporters.json_exporter import export_json
from great_generator.exporters.parquet_exporter import export_parquet
from great_generator.planning import ColumnTags, GenerationPlan, RealismReport
from great_generator.query_aware import (
    apply_query_aware_pandas,
    apply_query_aware_relational_pandas,
    has_query_aware_options,
    normalize_query_profile,
)
from great_generator.query_aware.validation import (
    validate_query_coverage as _validate_query_coverage,
)
from great_generator.recipes import generate_from_recipe as _generate_from_recipe
from great_generator.schema_inputs import (
    NormalizedSchemaInput,
    enforce_normalized_constraints,
    merge_custom_rules,
    normalize_data_dictionary,
    normalize_dbt_manifest,
    normalize_dbt_schema,
    normalize_json_schema,
)
from great_generator.schema_inputs import (
    load_data_dictionary as _load_data_dictionary,
)
from great_generator.schemas.generation import (
    active_spark_session,
    generate_domain_schema_pandas,
    generate_single_table_pandas,
    generate_single_table_spark,
    is_pyspark_dataframe,
    is_pyspark_struct_type,
    normalize_single_table_schema,
)
from great_generator.schemas.models import ContractSchema, DomainSchema, TableSchema
from great_generator.schemas.relational import relational_schema_from_specs
from great_generator.schemas.semantic import explain_generation_plan as _explain_generation_plan
from great_generator.schemas.semantic import validate_generated_data as _validate_generated_data
from great_generator.utils.validation import validate_engine, validate_output_format


def infer_generation_plan(
    schema: Any,
    *,
    advisor: str = "none",
    hints: dict | None = None,
    cache_path: str | Path = ".gg_cache/",
    refresh_cache: bool = False,
) -> GenerationPlan:
    """Create an editable generation plan for a schema."""

    from great_generator.advisors.registry import get_advisor

    selected = get_advisor(advisor, cache_path=cache_path, refresh_cache=refresh_cache)
    return selected.propose_plan(schema, hints=hints)


def tag_schema(
    schema: Any,
    *,
    advisor: str = "none",
    include_pii_classification: bool = True,
    include_business_semantics: bool = True,
    samples: dict | None = None,
    cache_path: str | Path = ".gg_cache/",
    refresh_cache: bool = False,
) -> ColumnTags:
    """Create editable column tags for a schema."""

    from great_generator.advisors.registry import get_advisor

    hints = {
        "include_pii_classification": bool(include_pii_classification),
        "include_business_semantics": bool(include_business_semantics),
    }
    sample_payload = dict(samples or {})
    if hints:
        sample_payload["_tagging_options"] = hints
    selected = get_advisor(advisor, cache_path=cache_path, refresh_cache=refresh_cache)
    return selected.tag_columns(schema, samples=sample_payload)


def review_realism(
    data: Any,
    plan: GenerationPlan,
    *,
    advisor: str = "none",
    sample_size: int = 500,
    cache_path: str | Path = ".gg_cache/",
) -> RealismReport:
    """Review a generated sample against a generation plan."""

    from great_generator.advisors.registry import get_advisor

    selected = get_advisor(advisor, cache_path=cache_path, refresh_cache=False)
    sample = _sample_for_realism_review(data, sample_size=sample_size)
    return selected.review_sample(sample, plan=plan, sample_size=sample_size)


def list_domains() -> list[str]:
    """Return available domain-pack names."""

    return sorted(DOMAIN_MODULES)


def get_domain_schema(domain: str) -> DomainSchema:
    """Return schema metadata for a domain pack."""

    try:
        module = DOMAIN_MODULES[domain]
    except KeyError as exc:
        raise ValueError(f"Unknown domain '{domain}'. Available domains: {list_domains()}") from exc
    return module.schema()


def parse_ddl(
    ddl_text: str,
    *,
    dialect: str | None = "ansi",
    strict: bool = True,
    name: str = "ddl_contract",
) -> ContractSchema:
    """Parse SQL CREATE TABLE DDL into a canonical contract."""

    from great_generator.contracts.ddl import parse_ddl as _parse_ddl

    return _parse_ddl(ddl_text, dialect=dialect, strict=strict, name=name)


def generate_domain(
    domain: str,
    engine: str = "pandas",
    scale: str = "tiny",
    rows: Mapping[str, int] | None = None,
    spark: Any | None = None,
    seed: int | None = None,
    realism: str = "realistic",
    anomalies: Mapping[str, float] | None = None,
    output_path: str | Path | None = None,
    output_format: str | None = None,
    partition_by: list[str] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
    return_labels: bool = False,
    history: str | None = None,
    history_window: str = "2y",
) -> dict[str, Any]:
    """Generate a complete synthetic domain."""

    validate_engine(engine)
    validate_output_format(output_format)
    realism = normalize_realism_mode(realism)
    validate_realism(realism)
    schema = get_domain_schema(domain)
    row_counts = resolve_row_counts(domain, scale, rows)
    module = DOMAIN_MODULES[domain]

    if engine == "pandas":
        from great_generator.engines.pandas_engine import generate_domain as generate_with_pandas

        data = generate_with_pandas(
            module,
            schema,
            row_counts,
            seed=seed,
            anomalies=anomalies,
            realism=realism,
            return_labels=return_labels,
        )
    else:
        if return_labels:
            raise ValueError("return_labels is currently supported for the pandas engine only.")
        from great_generator.engines.spark_engine import generate_domain as generate_with_spark

        data = generate_with_spark(
            domain,
            schema,
            row_counts,
            spark=spark,
            seed=seed,
            anomalies=anomalies,
            realism=realism,
        )

    if history is not None:
        if engine != "pandas":
            raise ValueError(
                "history generation is currently supported for the pandas engine only."
            )
        if history != "scd2":
            raise ValueError("Unsupported history mode. Use history='scd2'.")
        from great_generator.history import add_scd2_history_tables

        data = add_scd2_history_tables(data, schema, seed=seed, history_window=history_window)

    if output_path is not None:
        if output_format is None:
            raise ValueError("output_format is required when output_path is provided.")
        export_data(
            data,
            output_path=output_path,
            output_format=output_format,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    return data


def generate_relational(
    tables: Mapping[str, Any],
    relationships: list[str | Mapping[str, str]] | None = None,
    rows: Mapping[str, int] | int | None = None,
    engine: str = "pandas",
    spark: Any | None = None,
    seed: int | None = None,
    realism: str = "realistic",
    anomalies: Mapping[str, float] | None = None,
    output_path: str | Path | None = None,
    output_format: str | None = None,
    partition_by: list[str] | Mapping[str, Any] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
    return_labels: bool = False,
    required_values: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    ensure_join_coverage: bool = False,
    query_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a user-defined relational dataset and return table-name DataFrames.

    The primary workflow is DataFrame-first: callers receive a dictionary such as
    ``{"customers": customers_df, "orders": orders_df}`` and can use native pandas
    or Spark write APIs for CSV, JSON, Parquet, Delta, databases, catalog tables, or
    any destination supported by their runtime. ``output_path`` and ``output_format``
    are optional convenience exports.
    """

    validate_engine(engine)
    validate_output_format(output_format)
    realism = normalize_realism_mode(realism)
    validate_realism(realism)
    query_partition_by = partition_by if isinstance(partition_by, Mapping) else None
    export_partition_by = partition_by if not isinstance(partition_by, Mapping) else None
    query_aware_enabled = has_query_aware_options(
        required_values=required_values,
        partition_by=query_partition_by,
        target_selectivity=target_selectivity,
        query_profile=query_profile,
        ensure_join_coverage=ensure_join_coverage,
    )
    profile = normalize_query_profile(
        required_values=required_values,
        partition_by=query_partition_by,
        target_selectivity=target_selectivity,
        query_profile=query_profile,
        ensure_join_coverage=ensure_join_coverage,
    )

    schema, row_counts = relational_schema_from_specs(
        tables=tables,
        rows=rows,
        relationships=relationships,
    )

    if engine == "pandas":
        from great_generator.engines.pandas_engine import generate_domain as generate_with_pandas

        data = generate_with_pandas(
            domain_module=None,
            schema=schema,
            row_counts=row_counts,
            seed=seed,
            anomalies=anomalies,
            realism=realism,
            return_labels=return_labels,
        )
        if query_aware_enabled:
            data = apply_query_aware_relational_pandas(
                data,
                schema,
                profile,
                seed=seed,
            )
    else:
        if query_aware_enabled:
            raise ValueError(
                "Query-aware generation for generate_relational currently supports "
                "engine='pandas'. Generate pandas data first or omit query-aware options "
                "for Spark generation."
            )
        if return_labels:
            raise ValueError("return_labels is currently supported for the pandas engine only.")
        from great_generator.engines.spark_engine import generate_domain as generate_with_spark

        data = generate_with_spark(
            "custom_relational",
            schema,
            row_counts,
            spark=spark,
            seed=seed,
            anomalies=anomalies,
            realism=realism,
        )

    if output_path is not None:
        if output_format is None:
            raise ValueError("output_format is required when output_path is provided.")
        export_data(
            data,
            output_path=output_path,
            output_format=output_format,
            engine=engine,
            partition_by=export_partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )

    return data


def export_data(
    data: Mapping[str, Any],
    output_path: str | Path,
    output_format: str,
    engine: str = "pandas",
    partition_by: list[str] | None = None,
    mode: str = "overwrite",
    writer_options: Mapping[str, str] | None = None,
    num_partitions: int | None = None,
    partition_strategy: str = "repartition",
) -> None:
    """Export generated tables to table-per-folder outputs."""

    validate_engine(engine)
    validate_output_format(output_format)
    if output_format == "csv":
        export_csv(
            data,
            output_path,
            engine=engine,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "json":
        export_json(
            data,
            output_path,
            engine=engine,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "parquet":
        export_parquet(
            data,
            output_path,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    elif output_format == "delta":
        export_delta(
            data,
            output_path,
            engine=engine,
            partition_by=partition_by,
            mode=mode,
            writer_options=writer_options,
            num_partitions=num_partitions,
            partition_strategy=partition_strategy,
        )
    else:  # pragma: no cover - safeguarded by validate_output_format
        raise ValueError(f"Unsupported output format '{output_format}'.")


def generate_cdc(
    domain: str,
    table: str,
    rows: int,
    operations: list[str] | None = None,
    late_arrival_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate CDC-style records for supported domain/table pairs."""

    return _generate_cdc(
        domain=domain,
        table=table,
        rows=rows,
        operations=operations,
        late_arrival_rate=late_arrival_rate,
        duplicate_rate=duplicate_rate,
        seed=seed,
    )


def validate_query_coverage(
    data: Any,
    *,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    relationships: list[str | Mapping[str, str]] | None = None,
    ensure_join_coverage: bool = False,
    query_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate Query-Aware Generation coverage for generated data."""

    return _validate_query_coverage(
        data=data,
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        relationships=relationships,
        ensure_join_coverage=ensure_join_coverage,
        query_profile=query_profile,
    )


def generate_from_recipe(path: str | Path) -> dict[str, Any]:
    """Generate a dataset from a JSON, TOML, or simple YAML recipe file."""

    return _generate_from_recipe(path)


def generate_history(
    domain: str,
    table: str,
    scale: str = "tiny",
    rows: Mapping[str, int] | None = None,
    seed: int | None = None,
    realism: str = "realistic",
    history_window: str = "2y",
) -> pd.DataFrame:
    """Generate an SCD2 history table for one domain table."""

    from great_generator.history import generate_scd2_history

    data = generate_domain(
        domain,
        engine="pandas",
        scale=scale,
        rows=rows,
        seed=seed,
        realism=realism,
    )
    schema = get_domain_schema(domain)
    if table not in data or table not in schema.tables:
        raise ValueError(f"Unknown table '{table}' for domain '{domain}'.")
    primary_key = schema.tables[table].primary_key
    if primary_key is None:
        raise ValueError(f"Table '{table}' does not define a primary key.")
    return generate_scd2_history(
        data[table],
        natural_key=primary_key,
        seed=seed,
        history_window=history_window,
        namespace=f"{domain}.{table}",
    )


def generate_dimensional_model(
    domain: str,
    model: str = "star",
    grain: str | None = None,
    engine: str = "pandas",
    scale: str = "tiny",
    rows: Mapping[str, int] | None = None,
    spark: Any | None = None,
    seed: int | None = None,
    realism: str = "realistic",
) -> dict[str, Any]:
    """Generate a relational dimensional model with fact and dimension tables."""

    validate_engine(engine)
    from great_generator.models.dimensional import generate_dimensional_model as _generate

    source = generate_domain(
        domain,
        engine="pandas",
        scale=scale,
        rows=rows,
        seed=seed,
        realism=realism,
    )
    data = _generate(domain, source, model=model, grain=grain)
    if engine == "spark":
        spark_session = spark or active_spark_session()
        if spark_session is None:
            raise ValueError("Spark dimensional generation requires a SparkSession via spark=...")
        return {name: spark_session.createDataFrame(frame) for name, frame in data.items()}
    return data


def generate_data_vault_model(
    domain: str,
    engine: str = "pandas",
    scale: str = "tiny",
    rows: Mapping[str, int] | None = None,
    spark: Any | None = None,
    seed: int | None = None,
    realism: str = "realistic",
) -> dict[str, Any]:
    """Generate a relational Data Vault model with hubs, links, and satellites."""

    validate_engine(engine)
    from great_generator.models.data_vault import generate_data_vault_model as _generate

    schema = get_domain_schema(domain)
    source = generate_domain(
        domain,
        engine="pandas",
        scale=scale,
        rows=rows,
        seed=seed,
        realism=realism,
    )
    data = _generate(domain, source, schema)
    if engine == "spark":
        spark_session = spark or active_spark_session()
        if spark_session is None:
            raise ValueError("Spark Data Vault generation requires a SparkSession via spark=...")
        return {name: spark_session.createDataFrame(frame) for name, frame in data.items()}
    return data


def generate_from_schema(
    schema: ContractSchema | DomainSchema | TableSchema | pd.DataFrame | str | Any,
    rows: Mapping[str, int] | int = 100,
    seed: int | None = None,
    engine: str = "auto",
    spark: Any | None = None,
    table_name: str = "sample",
    realism: str = "realistic",
    domain: str | None = None,
    custom_rules: Mapping[str, Mapping[str, Any]] | None = None,
    plan: GenerationPlan | None = None,
    realistic: bool | None = None,
    validate: bool = False,
    return_report: bool = False,
    required_values: Mapping[str, Any] | None = None,
    partition_by: Mapping[str, Any] | None = None,
    target_selectivity: Mapping[str, Mapping[str, float]] | None = None,
    query_profile: Mapping[str, Any] | None = None,
) -> dict[str, pd.DataFrame] | pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    """Generate sample data from domain metadata, DataFrames, DDL strings, or Spark schemas.

    Supported inputs:
    - ``DomainSchema``: returns pandas tables, or Spark tables when ``spark=...``/``engine="spark"``.
    - ``TableSchema``: returns a pandas or Spark DataFrame.
    - ``Mapping[str, str]``: returns a pandas or Spark DataFrame from ``{column: dtype}``.
    - empty pandas ``DataFrame`` with dtypes: returns a pandas or Spark DataFrame.
    - DDL-like string such as ``"id int, name string"``: returns a pandas or Spark DataFrame.
    - PySpark ``StructType``: returns Spark when a SparkSession is provided or active.
    - PySpark ``DataFrame``: returns a Spark DataFrame and infers its SparkSession.
    """

    generation_rules = _rules_with_plan(custom_rules, plan)
    effective_realism = (
        "realistic" if realistic is True else "placeholder" if realistic is False else realism
    )
    effective_realism = normalize_realism_mode(effective_realism)
    validate_realism(effective_realism)
    query_aware_enabled = has_query_aware_options(
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        query_profile=query_profile,
    )
    profile = normalize_query_profile(
        required_values=required_values,
        partition_by=partition_by,
        target_selectivity=target_selectivity,
        query_profile=query_profile,
    )
    if engine == "auto":
        resolved_engine = "spark" if _has_spark_context(schema, spark) else "pandas"
    else:
        validate_engine(engine)
        resolved_engine = engine

    if isinstance(schema, str) and _looks_like_create_table_ddl(schema):
        schema = parse_ddl(schema, dialect="ansi", strict=True, name=table_name)

    if isinstance(schema, ContractSchema):
        if len(schema.tables) == 1 and not isinstance(rows, Mapping):
            table = next(iter(schema.tables.values()))
            return generate_from_schema(
                table,
                rows=int(rows),
                seed=seed,
                engine=resolved_engine,
                spark=spark,
                table_name=table.name,
                realism=effective_realism,
                domain=domain,
                custom_rules=custom_rules,
                plan=plan,
                validate=validate,
                return_report=return_report,
                required_values=required_values,
                partition_by=partition_by,
                target_selectivity=target_selectivity,
                query_profile=query_profile,
            )
        domain_schema = schema.to_domain_schema()
        return generate_from_schema(
            domain_schema,
            rows=rows,
            seed=seed,
            engine=resolved_engine,
            spark=spark,
            table_name=table_name,
            realism=effective_realism,
            domain=domain,
            custom_rules=custom_rules,
            plan=plan,
            validate=validate,
            return_report=return_report,
            required_values=required_values,
            partition_by=partition_by,
            target_selectivity=target_selectivity,
            query_profile=query_profile,
        )

    if isinstance(schema, DomainSchema):
        generated = generate_domain_schema_pandas(schema, rows=rows, seed=seed)
        if effective_realism == "realistic":
            from great_generator.core.realism import apply_realism_pandas

            generated = apply_realism_pandas(
                generated, schema, seed=seed, realism=effective_realism
            )
        if query_aware_enabled:
            generated = apply_query_aware_relational_pandas(
                generated,
                schema,
                profile,
                seed=seed,
            )
        if resolved_engine == "spark":
            if query_aware_enabled:
                raise ValueError(
                    "Query-aware generation for multi-table schema inputs currently "
                    "supports pandas output. Use engine='pandas' or omit query-aware "
                    "options for Spark output."
                )
            spark_session = spark or active_spark_session()
            if spark_session is None:
                raise ValueError("Spark schema generation requires a SparkSession via spark=...")
            spark_tables = {
                name: spark_session.createDataFrame(frame) for name, frame in generated.items()
            }
            return _maybe_attach_report(
                spark_tables,
                schema=schema,
                rules=generation_rules,
                validate=validate,
                return_report=return_report,
            )
        return _maybe_attach_report(
            generated,
            schema=schema,
            rules=generation_rules,
            validate=validate,
            return_report=return_report,
        )

    if isinstance(rows, Mapping):
        raise ValueError("Single-table schema generation expects rows to be an integer.")
    row_count = int(rows)
    if row_count < 0:
        raise ValueError("rows must be greater than or equal to zero.")

    if resolved_engine == "spark":
        if query_aware_enabled:
            raise ValueError(
                "Query-aware generation for generate_from_schema currently supports "
                "pandas output. Use engine='pandas' or omit query-aware options for "
                "Spark output."
            )
        spark_frame = generate_single_table_spark(
            schema,
            rows=row_count,
            spark=spark,
            seed=seed,
            table_name=table_name,
            realism=effective_realism,
            domain=domain,
            custom_rules=generation_rules,
            plan=plan,
        )
        return _maybe_attach_report(
            spark_frame,
            schema=schema,
            rules=generation_rules,
            validate=validate,
            return_report=return_report,
        )
    pandas_frame = generate_single_table_pandas(
        schema,
        rows=row_count,
        seed=seed,
        table_name=table_name,
        realism=effective_realism,
        domain=domain,
        custom_rules=generation_rules,
        plan=plan,
    )
    if query_aware_enabled:
        table, _source = normalize_single_table_schema(schema, table_name=table_name)
        pandas_frame = apply_query_aware_pandas(
            pandas_frame,
            table,
            profile,
            seed=seed,
        )
    return _maybe_attach_report(
        pandas_frame,
        schema=schema,
        rules=generation_rules,
        validate=validate,
        return_report=return_report,
    )


def generate_from_json_schema(
    schema: Mapping[str, Any] | str | Path,
    rows: int = 100,
    seed: int | None = None,
    strict: bool = True,
    table_name: str = "sample",
    **kwargs: Any,
) -> pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    """Generate synthetic data from a practical subset of JSON Schema.

    JSON Schema inputs are normalized into the existing ``generate_from_schema``
    path. Unsupported JSON Schema keywords raise a clear error by default.
    """

    normalized = normalize_json_schema(schema, strict=strict, table_name=table_name)
    return _generate_from_normalized_schema_input(
        normalized,
        rows=rows,
        seed=seed,
        table_name=table_name,
        **kwargs,
    )


def generate_from_dbt_schema(
    path: str | Path,
    model_name: str,
    rows: int = 100,
    seed: int | None = None,
    strict: bool = True,
    **kwargs: Any,
) -> pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    """Generate synthetic data from a dbt ``schema.yml`` model definition."""

    normalized = normalize_dbt_schema(path, model_name=model_name, strict=strict)
    table_name = str(kwargs.pop("table_name", model_name))
    return _generate_from_normalized_schema_input(
        normalized,
        rows=rows,
        seed=seed,
        table_name=table_name,
        **kwargs,
    )


def generate_from_dbt_manifest(
    path: str | Path,
    model_name: str,
    rows: int = 100,
    seed: int | None = None,
    strict: bool = True,
    **kwargs: Any,
) -> pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    """Generate synthetic data from a dbt ``target/manifest.json`` model node."""

    normalized = normalize_dbt_manifest(path, model_name=model_name, strict=strict)
    table_name = str(kwargs.pop("table_name", model_name))
    return _generate_from_normalized_schema_input(
        normalized,
        rows=rows,
        seed=seed,
        table_name=table_name,
        **kwargs,
    )


def load_data_dictionary(path: str | Path) -> dict[str, str]:
    """Load a CSV, YAML, or JSON data dictionary as a simple schema mapping."""

    return _load_data_dictionary(path)


def generate_from_data_dictionary(
    path: str | Path,
    rows: int = 100,
    seed: int | None = None,
    **kwargs: Any,
) -> pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    """Generate synthetic data from a CSV, YAML, or JSON data dictionary."""

    normalized = normalize_data_dictionary(path)
    table_name = str(kwargs.pop("table_name", "sample"))
    return _generate_from_normalized_schema_input(
        normalized,
        rows=rows,
        seed=seed,
        table_name=table_name,
        **kwargs,
    )


def _generate_from_normalized_schema_input(
    normalized: NormalizedSchemaInput,
    *,
    rows: int,
    seed: int | None,
    table_name: str,
    **kwargs: Any,
) -> pd.DataFrame | Any | tuple[Any, dict[str, Any]]:
    custom_rules = kwargs.pop("custom_rules", None)
    merged_rules = merge_custom_rules(normalized, custom_rules)
    result = generate_from_schema(
        normalized.schema,
        rows=rows,
        seed=seed,
        table_name=table_name,
        custom_rules=merged_rules,
        **kwargs,
    )
    if isinstance(result, tuple) and len(result) == 2:
        data, report = result
        return enforce_normalized_constraints(data, normalized, seed=seed), report
    return enforce_normalized_constraints(result, normalized, seed=seed)


def validate_generated_data(
    records: Any,
    schema: ContractSchema | TableSchema | Mapping[str, str] | pd.DataFrame | str | None = None,
    rules: Mapping[str, Mapping[str, Any]] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Validate generated schema data for common semantic quality checks."""

    schema_for_validation: TableSchema | Mapping[str, str] | str | pd.DataFrame | None
    if isinstance(schema, ContractSchema):
        schema_for_validation = (
            next(iter(schema.tables.values())) if len(schema.tables) == 1 else None
        )
    else:
        schema_for_validation = schema
    return _validate_generated_data(
        records, schema=schema_for_validation, rules=rules, strict=strict
    )


def explain_generation_plan(
    schema: ContractSchema | TableSchema | Mapping[str, str] | pd.DataFrame | str | Any,
    realism: str = "realistic",
    custom_rules: Mapping[str, Mapping[str, Any]] | None = None,
    table_name: str = "sample",
) -> dict[str, Any]:
    """Explain the semantic generation plan for a single-table schema."""

    if isinstance(schema, ContractSchema):
        if len(schema.tables) != 1:
            raise ValueError(
                "explain_generation_plan expects a one-table contract. "
                "Pass one table from contract.tables for multi-table contracts."
            )
        schema = next(iter(schema.tables.values()))
    table, _ = normalize_single_table_schema(schema, table_name=table_name)
    return _explain_generation_plan(
        table,
        realism=normalize_realism_mode(realism),
        custom_rules=custom_rules,
    )


def _maybe_attach_report(
    result: Any,
    schema: Any,
    rules: Mapping[str, Mapping[str, Any]] | None,
    validate: bool,
    return_report: bool,
) -> Any | tuple[Any, dict[str, Any]]:
    if not validate and not return_report:
        return result
    report = _validation_report_for_result(result, schema=schema, rules=rules)
    return (result, report) if return_report else result


def _validation_report_for_result(
    result: Any,
    schema: Any,
    rules: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    if isinstance(result, pd.DataFrame):
        return _validate_generated_data(result, schema=schema, rules=rules)
    if isinstance(result, Mapping):
        table_reports: dict[str, Any] = {}
        passed = True
        for table_name, frame in result.items():
            if isinstance(frame, pd.DataFrame):
                table_schema = None
                if isinstance(schema, (DomainSchema, ContractSchema)):
                    table_schema = schema.tables.get(table_name)
                table_report = _validate_generated_data(frame, schema=table_schema, rules=rules)
                table_reports[table_name] = table_report
                passed = passed and bool(table_report["passed"])
        return {
            "passed": passed,
            "errors": [],
            "warnings": [],
            "summary": {"tables_checked": len(table_reports)},
            "tables": table_reports,
        }
    return {
        "passed": True,
        "errors": [],
        "warnings": [
            "Validation report was not run locally because the result is not a pandas object."
        ],
        "summary": {"rows_checked": None, "columns_checked": None, "semantic_coverage": None},
    }


def _has_spark_context(schema: Any, spark: Any | None) -> bool:
    """Return true when auto mode should produce Spark DataFrames."""

    if spark is not None:
        return True
    if is_pyspark_dataframe(schema):
        return True
    return is_pyspark_struct_type(schema) and active_spark_session() is not None


def _looks_like_create_table_ddl(value: str) -> bool:
    normalized = " ".join(value.strip().lower().split())
    return normalized.startswith("create table ") or normalized.startswith(
        "create or replace table "
    )


def _rules_with_plan(
    custom_rules: Mapping[str, Mapping[str, Any]] | None,
    plan: GenerationPlan | None,
) -> dict[str, dict[str, Any]] | None:
    if plan is None:
        return {str(key): dict(value) for key, value in (custom_rules or {}).items()} or None
    rules = plan.to_custom_rules()
    for key, value in (custom_rules or {}).items():
        merged = dict(rules.get(str(key), {}))
        merged.update(dict(value))
        rules[str(key)] = merged
    return rules


def _sample_for_realism_review(data: Any, sample_size: int) -> dict[str, Any]:
    if isinstance(data, pd.DataFrame):
        return {"sample": data.head(sample_size).to_dict(orient="records")}
    if isinstance(data, Mapping):
        return {
            str(name): _sample_value_for_review(value, sample_size) for name, value in data.items()
        }
    return {"sample": _sample_value_for_review(data, sample_size)}


def _sample_value_for_review(value: Any, sample_size: int) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.head(sample_size).to_dict(orient="records")
    if hasattr(value, "limit") and hasattr(value, "toPandas"):
        return value.limit(sample_size).toPandas().to_dict(orient="records")
    if isinstance(value, list):
        return value[:sample_size]
    if isinstance(value, tuple):
        return list(value[:sample_size])
    return value
