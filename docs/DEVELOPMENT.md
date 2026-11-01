# Developing Gramson

## Files


- `spec/language.yaml`: selects the operator directories included in the language.
- `spec/core/*.yaml`: operator syntax, arities, names, titles, and summaries,
  grouped into data, logic, comparison, arithmetic, collection, string, and debugging.
  Longer descriptions are optional.
- `spec/extensions/*.yaml`: reusable optional extensions, selected explicitly by
  manifests through `include` (currently `gramson:bitwise`).
- `gramson/generation.py`: loads and composes specifications and generates schemas.
- `tools/generate_schema.py`: repository generation entry point used by `make generate`.
- `gramson/cli.py`: generates grammars and validates JSON or YAML expressions.
- `pyproject.toml`: package metadata, runtime dependencies, and the `gramson` command.
- `schema/expression.schema.yaml`: generated language entry point.
- `schema/core/*.schema.yaml`: generated named operator definitions, mirroring
  the source directories and file base names.
- `schema/shared.schema.yaml`: generated shared definitions such as `scalarLiteral`.
- `docs/json-value.schema.yaml`: hand-written result-data grammar.
- `examples/valid.json` and `examples/invalid.json`: accepted and rejected
  expressions; only each entry's `expression` is validated.
- `tests/test_validation.py`: metaschema and example validation.
- `tests/test_jsonlogic.py`: offline syntax compatibility checks against the
  pinned upstream [JSON Logic test corpus](../tests/vendor/jsonlogic/README.md),
  with its MIT license, provenance, checksums, and compatibility expectations.
- `tests/test_generation.py`: generation freshness, operator coverage, arities,
  shorthand, documentation, and registry validation.
- `tests/test_language.py`: directory selection, deterministic composition,
  collision diagnostics, mirrored output, and cross-group recursion.
- `tests/test_openapi.py`: external references, request validation, and result
  validation against the hand-written API contract.
- `docs/openapi.yaml`: hand-written placeholder `POST /evaluate` specification;
  its only schema components reference `expression` and `jsonValue`.
- `docs/index.html`: Swagger viewer; see [viewing instructions](README.md).
- `requirements-dev.txt`: generation, validation, YAML-reading, and Ruff linting dependencies.

## Layout and composition


```text
spec/                         schema/
  language.yaml                 expression.schema.yaml
                                shared.schema.yaml
  core/                         core/
    arithmetic.yaml               arithmetic.schema.yaml
    logic.yaml                    logic.schema.yaml
    ...                           ...
```

The repository manifest currently enables only its local `core`. Additional directories can be
enabled explicitly; operator sources are scanned recursively and sorted.
Duplicate operator keys or `schemaName` values are errors with both source
paths reported. Each group references the root expression grammar, allowing
nested expressions from every enabled group. See the specification guide for
manifest rules and custom output locations.

## Generate and validate


Requires Python 3.10 or newer. From the repository root:

```sh
make setup
make generate
make check
```

Run `make` or `make help` to list targets:

| Target | Purpose |
| --- | --- |
| `setup` | Create `.venv` and install the CLI and development dependencies. |
| `generate` | Generate the expression, shared, and operator JSON Schemas. |
| `example` | Generate and validate the included core extension example. |
| `example-bitwise` | Generate and validate the bitwise extension example. |
| `example-external` | Generate and validate a user-owned namespace include. |
| `lint` | Run Python and OpenAPI linting. |
| `lint-python` | Check Python code and import ordering with Ruff. |
| `lint-openapi` | Validate the hand-written OpenAPI document and external references with [openapi-spec-validator](https://openapi-spec-validator.readthedocs.io/en/stable/cli.html). |
| `test` | Run all tests, including schema validation and generation freshness. |
| `check` | Run lint and tests without rewriting generated files. |
| `setup-release` | Install development and release tooling. |
| `build` | Build a source archive and a wheel from that source archive. |
| `check-dist` | Build and check metadata, bundled schemas, and the installed CLI. |
| `serve` | Regenerate schemas and serve the Swagger viewer at `http://127.0.0.1:8765/docs/`. |

Override `PYTHON` or `VENV` for setup, or `HOST` and `PORT` for the viewer,
for example `make serve PORT=8000`. Run `make setup` before other targets.
The OpenAPI wrapper and JSON-value schema remain hand-written; `make generate`
only rebuilds the expression grammar. `make check` fails when generated schemas
are stale, so regenerate and commit them after changing operator sources.

[GitHub Actions](../.github/workflows/check.yml) runs `make check` on every push and
pull request with Python 3.10 and 3.14. CI checks the committed schemas without
regenerating them.
It also builds and verifies the wheel and source distribution. The
[release guide](RELEASING.md) documents local checks and the PyPI Trusted
Publishing setup. Publishing a matching GitHub release triggers the separate
publication workflow; routine pushes and pull requests only build and check.

Python linting uses Ruff, configured in `pyproject.toml` for Python 3.10 with
error, unused-code, and import-order checks. `make lint-python` checks without
rewriting files. To apply safe fixes locally, run `.venv/bin/python -m ruff check . --fix`.
Ruff is a development dependency; the installed CLI does not require it.

Generation uses PyYAML to read and write YAML. Tests use local schemas and bundled
metaschema support, with no remote schema fetches. The expression, shared, and grouped operator schemas are
generated; edit the OpenAPI and JSON-value schemas directly when their contracts
change. Tests assert syntax and data shape, not evaluation results.

