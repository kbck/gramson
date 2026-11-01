# Gramson

**Define JSON expression languages declaratively.**

Gramson compiles composable YAML operator definitions into recursive JSON Schema
grammars. Its CLI validates JSON or YAML expressions against the bundled grammar,
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
input or command usage errors. `python -m gramson validate ...` is also supported.

## Compatibility and contents

The included JSON Logic syntax profile covers all 34 documented operators plus
the `?:` alias. All 278 expressions in the pinned upstream corpus pass syntax
validation. Gramson applies stricter argument counts and object-shape rules than
the reference interpreter and validates every branch. There is no evaluator;
runtime equivalence is not tested.

The wheel includes the generated schemas under `gramson.schemas`, preserving
relative references for offline use. They can be accessed with
`importlib.resources.files("gramson.schemas")`. The source distribution also
contains the declarative specification, generator, tests, and documentation.

See the [repository and development guide](https://github.com/kbck/gramson#readme),
[operator specification](https://github.com/kbck/gramson/blob/main/spec/README.md),
and [issue tracker](https://github.com/kbck/gramson/issues).

## License and acknowledgements

Gramson is licensed under MIT. Its included expression language builds on
[JSON Logic](https://jsonlogic.com/), created by Jeremy Wadhams. The vendored
upstream tests retain their original MIT license and attribution; see the
[third-party notices](https://github.com/kbck/gramson/blob/main/THIRD_PARTY_NOTICES.md).
