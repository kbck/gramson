# Extend the core language

This ready-to-run example adds a unary `wrap` operator to Gramson's bundled
JSON Logic profile. The JSON and YAML `nested` expressions are equivalent:
core `+` contains custom `wrap` expressions, which contain core `var` and `+`
expressions. This demonstrates syntax composition; nothing is evaluated.

From the repository root (or an unpacked source distribution):

```sh
make setup
make example
```

The command generates ten schema files under `build/examples/extension/`, then
validates both `expressions/nested.json` and `expressions/nested.yaml`. Both should
print `valid expression` and exit with code `0`. Generated output stays in the
ignored `build/` directory.

## Run the steps yourself

After installing Gramson, activate the environment created by `make setup`:

```sh
. .venv/bin/activate
gramson generate --manifest examples/extension/language.yaml --output-directory build/examples/extension
gramson validate examples/extension/expressions/nested.yaml --schema build/examples/extension/expression.schema.yaml
gramson validate examples/extension/expressions/nested.json --schema build/examples/extension/expression.schema.yaml
```

`language.yaml` includes `gramson:core` and selects the local `custom/` directory.
`custom/wrapping.yaml` defines `wrap` with exactly one recursive expression
argument. The generated directory contains `core/`, `custom/`, shared
definitions, and one expression entry point. You can move the whole directory
and continue validating offline with its entry point.

Try an invalid call:

```sh
gramson validate examples/extension/expressions/invalid-arity.yaml --schema build/examples/extension/expression.schema.yaml
```

This must fail with exit code `1`: `wrap` received two arguments instead of one.
Without `--schema`, the bundled core grammar also rejects the `nested`
expressions because it does not define `wrap`.

## Use the same operator without core

`standalone.yaml` selects the same custom declarations without `include`:

```sh
gramson generate --manifest examples/extension/standalone.yaml --output-directory build/examples/standalone
gramson validate examples/extension/expressions/wrap-only.yaml --schema build/examples/standalone/expression.schema.yaml
```

That expression is valid. Validating `nested.yaml` against the standalone grammar
must fail with code `1`, because core operators are absent.

To adapt this example, copy this directory into your project, edit the custom
declarations and expressions, and regenerate. Operator directories are relative
to each manifest, so the example does not depend on the repository's `spec/`
directory. Bundled core definitions come from the installed Gramson version.
