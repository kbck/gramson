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
[spec/core](spec/core), and [generator](gramson/generation.py) are the
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

Validation uses the bundled generated grammar by default and resolves references locally,
without network requests. Success is printed to stdout; failures go to stderr
with an expression location. Exit codes are `0` for valid syntax, `1` for an
invalid expression, and `2` for input, schema, or command usage errors. It does not evaluate
expressions. `python -m gramson validate ...` is also supported after installation.

## Define your own language

Start with the [ready-to-run extension example](examples/extension/README.md):

```sh
make setup
make example
```

It includes manifests for extending core and defining an independent language,
a custom operator, equivalent JSON/YAML expressions, and an invalid example.
Generated files go under the ignored `build/` directory.

The [bitwise extension](examples/bitwise/README.md) adds `&`, `|`, `^`, `~`, `<<`,
and `>>`, plus `hexToInt` and `intToHex` conversions, alongside core. Its reusable
declarations live in
[`spec/extensions/bitwise.yaml`](spec/extensions/bitwise.yaml) and are bundled
with the installed package. Run the example with `make example-bitwise`, or
select the extension in your own manifest:

```yaml
include:
  - gramson:core
  - gramson:bitwise
```

You can also add `operatorDirectories` to combine bundled extensions with your
own declarations. Including only `gramson:bitwise` selects its eight operators
alongside the standard literals and arrays, without core.

For a user-owned specification library, use a namespace and a search root:

```yaml
include:
  - gramson:core
  - mystuff:myops
```

```sh
gramson generate --manifest language.yaml --spec-path ./vendor --output-directory generated
```

This loads declarations recursively from `vendor/mystuff/myops/`. Repeat
`--spec-path` for multiple libraries; relative paths are resolved from the
command's working directory. `gramson:` is reserved for this package. Unknown
includes and ambiguous matches across search roots fail generation; search-path
order gives no precedence. Namespaces select sources without prefixing operator
keys. Generated schemas remain self-contained, with external groups emitted
under `mystuff/myops/`.

Try the [ready-to-run external library example](examples/external/README.md)
with `make example-external`.

Generate the bundled core language into a self-contained directory:

```sh
gramson generate --output-directory generated
```

To extend it in your own project, create `my-language/language.yaml`:

```yaml
include:
  - gramson:core
operatorDirectories:
  - custom
```

Then define an operator in `my-language/custom/wrapping.yaml`:

```yaml
wrap:
  schemaName: wrapper
  title: Wrapper
  summary: Wrap one expression.
  argumentKind: expression
  minArgs: 1
  maxArgs: 1
```

Generate the composed grammar and validate against its entry point:

```sh
gramson generate --manifest my-language/language.yaml --output-directory generated
gramson validate expression.yaml --schema generated/expression.schema.yaml
printf '%s\n' '{"wrap":[{"+":[1,2]}]}' | gramson validate - --schema generated/expression.schema.yaml
```

The output contains core and custom operator schemas, shared definitions, and
one root expression grammar. Core and custom operators can nest in each other.
Move or distribute the whole output directory together; validation uses its
local files without consulting the installed core language or making network
requests. Without `--schema`, validation still uses the bundled core grammar.

A manifest without `include` defines a language using only its selected local
directories. `include: [gramson:core]` selects just core. Bundled declarations use
the installed Gramson version, so pin that version alongside your manifest for
reproducible builds. Include order gives no precedence: duplicate operator keys,
definition names, or output paths fail generation before schemas are written.
Declarations define syntax, not evaluation behavior.

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

[GitHub Actions](.github/workflows/check.yml) runs `make check` on every push and
pull request with Python 3.10 and 3.14. CI checks the committed schemas without
regenerating them.
It also builds and verifies the wheel and source distribution. The
[release guide](docs/RELEASING.md) documents local checks and the PyPI Trusted
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
