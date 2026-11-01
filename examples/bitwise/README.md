# Bitwise extension

This extension adds six bitwise operator forms to Gramson's core language.

The reusable declarations live in
[`spec/extensions/bitwise.yaml`](../../spec/extensions/bitwise.yaml) and are
included in the installed package. This directory contains the example manifest
and expressions. Any project can select the extension without copying its declarations:

```yaml
include:
  - gramson:core
  - gramson:bitwise
```

Available operators:

| Operator | Definition name | Arguments | Non-array shorthand |
| --- | --- | --- | --- |
| `&` | `bitwiseAnd` | Exactly two | No |
| `\|` | `bitwiseOr` | Exactly two | No |
| `^` | `bitwiseXor` | Exactly two | No |
| `~` | `bitwiseNot` | Exactly one | Yes |
| `<<` | `bitwiseLeftShift` | Exactly two | No |
| `>>` | `bitwiseRightShift` | Exactly two | No |

All operands are recursive expressions. The JSON and YAML examples use all six
operators, nested with core `if`, `!=`, and `var` forms.

From the repository root (or an unpacked source distribution):

```sh
make setup
make example-bitwise
```

This generates ten schema files in `build/examples/bitwise/` and validates both
`expressions/nested.yaml` and `expressions/nested.json`. Each should print
`valid expression` and exit with code `0`.
The bitwise definitions are emitted as `extensions/bitwise.schema.yaml` alongside
the core groups and the combined expression entry point.

To run the commands yourself after activating the installed CLI:

```sh
. .venv/bin/activate
gramson generate --manifest examples/bitwise/language.yaml --output-directory build/examples/bitwise
gramson validate examples/bitwise/expressions/nested.yaml --schema build/examples/bitwise/expression.schema.yaml
gramson validate examples/bitwise/expressions/nested.json --schema build/examples/bitwise/expression.schema.yaml
```

`expressions/invalid-arity.yaml` must fail with code `1` against this grammar:
`&` requires two arguments. The bundled core grammar rejects bitwise calls unless
you select the generated extension grammar with `--schema`.

## Names and collisions

These keys do not collide with core operators: `&` and `|` differ from `and` and
`or`, `~` differs from `!`, and `<<` and `>>` differ from `<` and `>`. Their six
definition names also differ from all core `schemaName` values. The composed
language has 41 operator keys: 35 from core and six from this extension.

Generation rejects duplicate operator keys or definition names across all
selected groups, including core. There are no implicit overrides.
Quote symbolic operator keys in YAML; in particular, unquoted `~` represents
null and unquoted `<<` has YAML merge-key meaning.

This extension defines syntax only. Operand types, integer conversion, bit
width, signedness, shift-count handling, and evaluation remain unspecified.
It does not add these operators to JSON Logic's documented core or implement
an evaluator.
