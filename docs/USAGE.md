# Using Gramson

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


Start with the [ready-to-run extension example](../examples/extension/README.md):

```sh
make setup
make example
```

It includes manifests for extending core and defining an independent language,
a custom operator, equivalent JSON/YAML expressions, and an invalid example.
Generated files go under the ignored `build/` directory.

The [bitwise extension](../examples/bitwise/README.md) adds `&`, `|`, `^`, `~`, `<<`,
and `>>`, plus `hexToInt` and `intToHex` conversions, alongside core. Its reusable
declarations live in
[`spec/extensions/bitwise.yaml`](../spec/extensions/bitwise.yaml) and are bundled
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

Try the [ready-to-run external library example](../examples/external/README.md)
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

