# Gramson

**Define JSON expression languages declaratively.**

Gramson compiles composable YAML operator definitions into recursive JSON Schema
grammars. Its CLI generates languages and validates JSON or YAML expressions,
with readable error locations and no network requests during validation.

## Install and validate

Requires Python 3.10 or newer. Install in a virtual environment:

```sh
python -m pip install gramson
gramson validate expression.json
gramson validate expression.yaml
```

For example, `expression.yaml` can contain:

```yaml
if:
  - '>':
      - var: age
      - 18
  - adult
  - minor
```

Read one expression from stdin:

```sh
printf '%s\n' '{"var":"price"}' | gramson validate -
printf '%s\n' 'var: price' | gramson validate --format yaml -
```

Files ending in `.yaml` or `.yml` are read as YAML; other files and stdin default
to JSON. Use `--format json` or `--format yaml` to override detection. Each input
contains one expression, without an API request envelope. YAML values must be
representable as JSON: duplicate or non-string keys, non-finite numbers,
timestamps, and cyclic aliases are rejected. Quote dates to use them as strings.

Exit codes are `0` for valid syntax, `1` for an invalid expression, and `2` for
input, schema, or command usage errors. `python -m gramson validate ...` is also supported.

## Generate and extend a language

The [ready-to-run extension example](https://github.com/kbck/gramson/tree/main/examples/extension)
contains manifests, a custom operator, JSON/YAML expressions, and instructions.
It is also included in the source distribution; run `make setup` and `make example`
from its repository or source-distribution root.
The [bitwise extension](https://github.com/kbck/gramson/tree/main/examples/bitwise)
adds `&`, `|`, `^`, `~`, `<<`, `>>`, `hexToInt`, and `intToHex`;
run it with `make example-bitwise`.
Its reusable declarations are bundled in Gramson and can be selected directly:

```yaml
include:
  - gramson:core
  - gramson:bitwise
```

No declaration copying is needed. Add `operatorDirectories` for local groups,
or include only `gramson:bitwise` to select it without core. Duplicate includes,
unknown names, and operator, definition-name, or output-path collisions are errors.

`gramson generate --output-directory generated` writes the bundled core grammar
as a self-contained directory. For a custom language, create a manifest:

```yaml
# my-language/language.yaml
include:
  - gramson:core
operatorDirectories:
  - custom
```

Add declarations in `my-language/custom/wrapping.yaml`:

```yaml
wrap:
  schemaName: wrapper
  title: Wrapper
  summary: Wrap one expression.
  argumentKind: expression
  minArgs: 1
  maxArgs: 1
```

```sh
gramson generate --manifest my-language/language.yaml --output-directory generated
gramson validate expression.yaml --schema generated/expression.schema.yaml
```

Generated output includes core and custom schemas, shared definitions, and one
expression entry point; operators can nest across groups. Keep the output
directory together when moving it. Validation against `--schema` uses those
files offline and does not depend on the installed core language.

Without `include`, a manifest selects only local directories.
`include: [gramson:core]` alone selects just core. Include order does not give
precedence: duplicate operator keys, definition names, or output paths fail the
whole generation. Pin the Gramson version for reproducible bundled declarations.
Custom declarations define syntax; they do not implement evaluation.

## Compatibility and contents

The included JSON Logic syntax profile covers all 34 documented operators plus
the `?:` alias. All 278 expressions in the pinned upstream corpus pass syntax
validation. Gramson applies stricter argument counts and object-shape rules than
the reference interpreter and validates every branch. There is no evaluator;
runtime equivalence is not tested.

The wheel includes the generated schemas under `gramson.schemas`, preserving
relative references for offline use. They can be accessed with
`importlib.resources.files("gramson.schemas")`. Core and optional extension declarations are bundled
under `gramson.specs`, and the generator is included in the installed package.
The source distribution also contains tests and user documentation.

See the [repository and development guide](https://github.com/kbck/gramson#readme),
[operator specification](https://github.com/kbck/gramson/blob/main/spec/README.md),
and [issue tracker](https://github.com/kbck/gramson/issues).

## License and acknowledgements

Gramson is licensed under MIT. Its included expression language builds on
[JSON Logic](https://jsonlogic.com/), created by Jeremy Wadhams. The vendored
upstream tests retain their original MIT license and attribution; see the
[third-party notices](https://github.com/kbck/gramson/blob/main/THIRD_PARTY_NOTICES.md).
