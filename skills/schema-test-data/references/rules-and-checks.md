# Supported controls and explicit checks

Use `custom_rules={column: rule}` with `generate_from_schema`. Check installed
support rather than inventing rule names.

| Request | Rule | Validate after generation |
|---|---|---|
| Numeric bounds | `{"min": 0, "max": 100}` | Non-null values in range |
| Category mix | `{"values": [...]}` or `{"weighted_values": {"A": .8, "B": .2}}` | Allowed values, observed rates; random rates are not exact counts |
| Date interval | `{"start": "2026-01-01", "end": "2026-01-31"}` | Bounds and types; make time context explicit |
| Name-like alias | `{"type": "full_name"}` | Shape/semantic plausibility, not a claim about real people |
| ID format | `{"prefix": "CUST"}` or `{"pattern": "CUST-{index:06d}"}` | Uniqueness and format |
| Nulls | `{"null_rate": .02}` on supported non-ID fields | Count, expected variation, schema still permits nulls |
| Unique | `{"unique": True}` is a validation expectation | Verify, never assume all arbitrary columns become unique |

`pattern` is a format template, **not a regex generator**. For a user-supplied
regex, explain this limit and ask for a template or validate an explicitly agreed
fixture construction. SQL constraints and column names are not permission to
evaluate Python or arbitrary SQL.

The semantic engine supplies reasonable defaults for many names/emails/dates.
Do not replace its behavior with hardcoded domain assumptions. Some semantic dates
use the current day; pin explicit windows and environment for repeatable long-lived
fixtures. Inspect correlated/date-derived fields even when a window is supplied.

Pandas checks can use `.is_unique`, `.isna()`, `.isin()` and `.between()`. Only
check declared keys as unique. For relationships use explicit PK/FK checks or
the relational skill. Generic validation does not replace these checks.

Output normally remains `df` so users choose their writer. For requested local
CSV/JSON/Parquet, preserve indexes only intentionally and prevent overwrites.
`export_data` defaults to overwrite: pass an explicit safe mode. `export_dataset`
is an unreleased helper on the audited main branch and not a prerequisite for
these skills. Spark Delta requires a configured runtime; cloud auth belongs to
the user's environment. Manifests describe provenance; they are not data hashes.
