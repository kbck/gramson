# Gramson

**Define JSON expression languages in YAML. Generate JSON Schema to validate them.**

Describe each operator's arguments in YAML, and Gramson turns those declarations
into a grammar that checks JSON expressions, including nested ones. Combine
operator groups from your own files, shared libraries, or the included JSON Logic
profile to define your language.

Gramson defines and validates syntax. It does not evaluate expressions.

## How it works

Declare an operator that takes exactly one expression:

```yaml
wrap:
  argumentKind: expression
  minArgs: 1
  maxArgs: 1
```

Combine it with the bundled core language, and the generated schema accepts:

```json
{"wrap": [{"+": [1, 2]}]}
```

It rejects `{"wrap": [1, 2]}` because `wrap` takes one argument. Recursive
references let your operators nest inside core operators, and vice versa.
The output is standard Draft 2020-12 JSON Schema, usable with other validators.

## Try it

Requires Python 3.10 or newer. From a checkout:

```sh
make setup
make example
```

This installs the CLI, generates a language with `wrap`, and validates the
included JSON and YAML expressions. The [complete example](examples/extension/README.md)
contains the manifest, declarations, and expressions ready to edit.

For your own files, the workflow is:

```sh
. .venv/bin/activate
gramson generate --manifest language.yaml --output-directory generated
gramson validate expression.yaml --schema generated/expression.schema.yaml
```

Generated output is self-contained and validates offline. Without `--schema`,
validation uses the bundled core grammar. See the [usage guide](docs/USAGE.md)
for input formats, stdin, exit codes, and custom languages.

## Compose a language

Select bundled groups and local declarations in a manifest:

```yaml
include:
  - gramson:core
  - gramson:bitwise
operatorDirectories:
  - custom
```

- **Core:** a JSON Logic syntax profile covering 34 documented operators plus
  `?:`. All 278 expressions in the pinned upstream corpus pass syntax validation.
  Structural rules are stricter than the reference interpreter; runtime
  equivalence is untested.
- **Bitwise:** six bitwise operators plus `hexToInt` and `intToHex` conversion
  forms. Try `make example-bitwise`.
- **Your libraries:** include names such as `mystuff:myops` with explicit
  `--spec-path` search roots. Try `make example-external`.

Include order gives no precedence: duplicate operator keys, definition names,
or output paths fail generation. The [specification guide](spec/README.md)
explains declarations and include resolution.

## Documentation

- [Usage and CLI](docs/USAGE.md)
- [Operator specification and manifest format](spec/README.md)
- [Scope, compatibility boundaries, and open questions](docs/DESIGN.md)
- [Development commands and repository layout](docs/DEVELOPMENT.md)
- [Swagger schema viewer](docs/README.md)

To work on Gramson, run `make check` for Ruff, OpenAPI validation, and tests.
Run `make help` for all targets.

## License and acknowledgements

[MIT](LICENSE). The included JSON Logic profile builds on
[JSON Logic](https://jsonlogic.com/), created by Jeremy Wadhams. Its shared test
corpus is vendored with the original MIT license and attribution; see
[third-party notices](THIRD_PARTY_NOTICES.md).
