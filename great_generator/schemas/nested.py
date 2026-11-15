"""Flatten nested relational specifications into flat tables and relationships."""

from collections.abc import Mapping
from typing import Any

from great_generator.schemas.relational import relational_schema_from_specs


def flatten_nested_spec(nested_spec: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Flatten a hierarchical specification into table specs and FK relationships.

    A child table may set ``fk`` to choose its foreign-key column. The default FK
    name is ``{parent_table}_id``. Parent primary keys are resolved from their
    schema, including non-conventional names.
    """
    if not isinstance(nested_spec, Mapping):
        raise ValueError("nested_spec must be a mapping of table names to table specifications.")

    tables: dict[str, Any] = {}
    relationships: list[str] = []

    def walk(node: Mapping[str, Any], parent: tuple[str, str] | None = None) -> None:
        if not isinstance(node, Mapping):
            raise ValueError("'children' must be a mapping of table names to table specifications.")

        for table_name, spec in node.items():
            if not isinstance(spec, Mapping):
                raise ValueError(f"Table specification for '{table_name}' must be a mapping.")
            if not isinstance(table_name, str) or not table_name.strip():
                raise ValueError("Table names must be non-empty strings.")
            if table_name in tables:
                raise ValueError(f"Duplicate table name '{table_name}' in nested specification.")
            if "schema" not in spec and "columns" not in spec:
                raise ValueError(f"Table '{table_name}' is missing the required 'schema' key.")

            table_spec = dict(spec)
            children = table_spec.pop("children", {})
            table_spec.pop("fk", None)

            # Resolve primary-key metadata using the same parser used by generation.
            parsed_schema, _ = relational_schema_from_specs({table_name: table_spec}, rows=0)
            parsed_table = parsed_schema.tables[table_name]
            primary_key = parsed_table.primary_key

            if parent is not None:
                parent_name, parent_pk = parent
                fk_col = spec.get("fk", f"{parent_name}_id")
                if not isinstance(fk_col, str) or not fk_col.strip():
                    raise ValueError(
                        f"The 'fk' value for table '{table_name}' must be a non-empty string."
                    )
                fk_col = fk_col.strip()

                child_column_names = {column.name for column in parsed_table.columns}
                if fk_col not in child_column_names:
                    schema = table_spec.get("schema", table_spec.get("columns"))
                    if not isinstance(schema, str):
                        raise ValueError(
                            f"Cannot automatically add foreign key '{fk_col}' to non-string schema "
                            f"for table '{table_name}'. Declare the FK column in the schema."
                        )
                    table_spec["schema"] = f"{schema}, {fk_col} int"
                else:
                    child_column = next(
                        column for column in parsed_table.columns if column.name == fk_col
                    )
                    parent_table = relational_schema_from_specs(
                        {parent_name: tables[parent_name]}, rows=0
                    )[0].tables[parent_name]
                    parent_column = next(
                        column for column in parent_table.columns if column.name == parent_pk
                    )
                    if child_column.dtype != parent_column.dtype:
                        raise ValueError(
                            f"Foreign key column '{table_name}.{fk_col}' has type "
                            f"'{child_column.dtype}', but parent key '{parent_name}.{parent_pk}' "
                            f"has type '{parent_column.dtype}'."
                        )

                # Store the relationship in the parent->child format expected by
                # generate_relational, preserving the actual parent PK name.
                relationships.append(f"{table_name}.{fk_col} -> {parent_name}.{parent_pk}")

            tables[table_name] = table_spec
            walk(children, (table_name, primary_key))

    walk(nested_spec)
    return tables, relationships
