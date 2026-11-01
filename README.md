# Gramson

**Define JSON languages declaratively.**

Gramson is a language-definition toolchain: declare operators and their argument
forms in YAML, compose them through a language manifest, and compile them into a
recursive JSON Schema grammar. JSON parsing supplies the expression tree;
standard JSON Schema validators check whether that tree belongs to the language.
Operator groups can be combined, and their expressions can nest across groups.

The included expression language covers the syntax of all 34
[documented JSON Logic operators](https://jsonlogic.com/operations.html).
It also supports `?:` as an alias for `if`.
Gramson currently defines and validates syntax; it does not evaluate expressions
or implement semantic typing.

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
| `setup` | Create `.venv` and install development dependencies. |
| `generate` | Generate the expression, shared, and operator JSON Schemas. |
| `lint` / `lint-openapi` | Validate the hand-written OpenAPI document and external references with [openapi-spec-validator](https://openapi-spec-validator.readthedocs.io/en/stable/cli.html). |
| `test` | Run all tests, including schema validation and generation freshness. |
| `check` | Run lint and tests without rewriting generated files. |
| `serve` | Regenerate schemas and serve the Swagger viewer at `http://127.0.0.1:8765/docs/`. |

Override `PYTHON` or `VENV` for setup, or `HOST` and `PORT` for the viewer,
for example `make serve PORT=8000`. Run `make setup` before other targets.
The OpenAPI wrapper and JSON-value schema remain hand-written; `make generate`
only rebuilds the expression grammar. `make check` fails when generated schemas
are stale, so regenerate and commit them after changing operator sources.

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
