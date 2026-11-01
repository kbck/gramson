# Gramson

**Define JSON languages declaratively.**

Gramson is a language-definition toolchain: declare operators and their argument
forms in YAML, compose them through a language manifest, and compile them into a
recursive JSON Schema grammar. JSON parsing supplies the expression tree;
standard JSON Schema validators check whether that tree belongs to the language.
Operator groups can be combined, and their expressions can nest across groups.

The included JSON Logic syntax profile covers all 34
[documented operators](https://jsonlogic.com/operations.html) plus the `?:` alias.
All 278 expressions in the [pinned upstream test corpus](tests/vendor/jsonlogic/README.md)
pass validation. Gramson applies stricter structural rules than the reference
interpreter, including argument-count constraints, rejection of object literals,
and validation of every branch. It does not evaluate expressions or implement
semantic typing; runtime equivalence is not tested.

Gramson is licensed under the [MIT License](LICENSE). The vendored upstream
tests retain their MIT license and attribution; see
[third-party notices](THIRD_PARTY_NOTICES.md).

The [language manifest](spec/language.yaml), operator definitions in
[spec/core](spec/core), and [generator](tools/generate_schema.py) are the
authoritative specification. The manifest selects operator directories.
The [expression schema](schema/expression.schema.yaml) is generated Draft
2020-12 JSON Schema: edit the operator definitions and regenerate rather than changing
the schema by hand. The [specification guide](spec/README.md) describes the
registry format, supported forms, and compatibility boundaries.

## Validate an expression

Install from this checkout with `make setup`, then activate the environment:

```sh
. .venv/bin/activate
gramson validate expression.json
gramson validate expression.yaml
printf '%s\n' '{"var":"price"}' | gramson validate -
printf '%s\n' 'var: price' | gramson validate --format yaml -
```

Each input contains one expression, without a request envelope or example-list
wrapper. Files ending in `.yaml` or `.yml` are read as YAML; other files and stdin
default to JSON. Use `--format json` or `--format yaml` to override detection.
For example, `expression.yaml` could contain:

```yaml
if:
  - '>':
      - var: age
      - 18
  - adult
  - minor
```

YAML is an alternative way to write JSON values, not a separate expression
language. Quote operator keys when YAML syntax requires it, such as `'!'` and
`'?:'`. Object keys must be strings; duplicate keys, non-finite numbers,
YAML-only values such as timestamps, and cyclic aliases are rejected as input
errors. Quote a date to use it as a string. Empty input is rejected; use `null`
for a null expression.

Validation uses the bundled generated grammar and resolves references locally,
without network requests. Success is printed to stdout; failures go to stderr
with an expression location. Exit codes are `0` for valid syntax, `1` for an
invalid expression, and `2` for input or command usage errors. It does not evaluate
expressions. `python -m gramson validate ...` is also supported after installation.

## Scope and decisions

- Accept JSON scalar literals and recursive arrays of expressions.
- Represent each operation as a closed object with exactly one registered key.
- Support data access, conditionals, Boolean logic, comparisons, arithmetic,
  collections, strings, and logging syntax.
- Accept variable defaults, numeric and computed keys, unary shorthand, and
  the documented arity profile.
- Reject unknown operators and arbitrary object literals throughout expressions,
  including inside arrays, defaults, and unselected branches.

This specifies structural acceptance. It does not implement evaluation or
semantic typing. For example, `{"+": [true, "2", null]}` and
`{"map": [true, "body"]}` pass syntax validation without promising meaningful
evaluation. The profile constrains arities rather than accepting every malformed
call that a permissive interpreter might process.

`if` and its `?:` alias accept condition/result pairs with an optional final fallback. The agreed
runtime result is `null` when no condition matches and no fallback is supplied;
there is no evaluator yet to execute that rule.
Empty argument lists are accepted and yield `null` in JSON Logic. A single
argument is a fallback expression; non-array shorthand is also accepted.

Results are data rather than expressions. The hand-written
[JSON-value schema](docs/json-value.schema.yaml) accepts scalars, recursive
arrays, and arbitrary objects. It reuses `scalarLiteral` from the generated shared schema
but defines its own recursive containers so result objects are never treated as
operator calls.

## Files

- `spec/language.yaml`: selects the operator directories included in the language.
- `spec/core/*.yaml`: operator syntax, arities, names, titles, and summaries,
  grouped into data, logic, comparison, arithmetic, collection, string, and debugging.
  Longer descriptions are optional.
- `tools/generate_schema.py`: generates the expression grammar.
- `gramson/cli.py`: validates JSON or YAML expressions using the bundled grammar.
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
  pinned upstream [JSON Logic test corpus](tests/vendor/jsonlogic/README.md),
  with its MIT license, provenance, checksums, and compatibility expectations.
- `tests/test_generation.py`: generation freshness, operator coverage, arities,
  shorthand, documentation, and registry validation.
- `tests/test_language.py`: directory selection, deterministic composition,
  collision diagnostics, mirrored output, and cross-group recursion.
- `tests/test_openapi.py`: external references, request validation, and result
  validation against the hand-written API contract.
- `docs/openapi.yaml`: hand-written placeholder `POST /evaluate` specification;
  its only schema components reference `expression` and `jsonValue`.
- `docs/index.html`: Swagger viewer; see [viewing instructions](docs/README.md).
- `requirements-dev.txt`: generation, validation, and YAML-reading dependencies.

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

The manifest currently enables only `core`. Additional directories can be
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
| `lint` / `lint-openapi` | Validate the hand-written OpenAPI document and external references with [openapi-spec-validator](https://openapi-spec-validator.readthedocs.io/en/stable/cli.html). |
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

[GitHub Actions](.github/workflows/check.yml) runs `make check` on every push and
pull request with Python 3.10 and 3.14. CI checks the committed schemas without
regenerating them.
It also builds and verifies the wheel and source distribution. The
[release guide](docs/RELEASING.md) documents local checks and the PyPI Trusted
Publishing setup. Publishing a matching GitHub release triggers the separate
publication workflow; routine pushes and pull requests only build and check.

Generation uses PyYAML to read and write YAML. Tests use local schemas and bundled
metaschema support, with no remote schema fetches. The expression, shared, and grouped operator schemas are
generated; edit the OpenAPI and JSON-value schemas directly when their contracts
change. Tests assert syntax and data shape, not evaluation results.

## Open design questions

- **Semantic typing:** Should a separate phase check operand and result types?
  How would it learn variable types and handle null or missing values?
- **Explicit conversions:** This remains the preferred direction. Unary `+` and
  `!!` are accepted syntax, but conversion failures and implicit coercions
  remain undecided.
- **Named constants:** Are they needed, and how should they be represented,
  scoped, and distinguished from external data?
- **Custom operator extensions:** The registry describes build-time syntax.
  Runtime loading, namespaces, and versioning remain unspecified.
- **Evaluation and compatibility:** Lookup, truthiness, arithmetic, equality,
  collection scope, short-circuiting, and errors require decisions. The
  no-fallback `if` result is settled as `null`.

## Next steps

Settle semantic typing, conversions, and runtime compatibility before building
an evaluator. For each syntax change, update the relevant operator file, regenerate the
schemas, and add accepted and rejected examples.

## Acknowledgements

Gramson's included expression language builds on [JSON Logic](https://jsonlogic.com/),
created by Jeremy Wadhams. Its operator forms and shared test corpus provide the
basis for Gramson's JSON Logic syntax compatibility checks.

The upstream test corpus is vendored with its original MIT license and copyright
notice. See the [snapshot provenance](tests/vendor/jsonlogic/README.md) and
[third-party notices](THIRD_PARTY_NOTICES.md).
