# Bitwise extension

This extension adds six bitwise operator forms and two explicit hexadecimal
conversion forms to Gramson's core language.

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
| `hexToInt` | `hexToInt` | Exactly one | Yes |
| `intToHex` | `intToHex` | Exactly one | Yes |

All operands are recursive expressions. The JSON and YAML `nested` examples use
all six bitwise operators, nested with core `if`, `!=`, and `var` forms.
The `conversions` examples combine both conversion operators with bitwise AND
and a variable expression.

From the repository root (or an unpacked source distribution):

```sh
make setup
make example-bitwise
```

This generates ten schema files in `build/examples/bitwise/` and validates the
JSON and YAML versions of `expressions/nested` and `expressions/conversions`.
Each should print
`valid expression` and exit with code `0`.
The bitwise definitions are emitted as `extensions/bitwise.schema.yaml` alongside
the core groups and the combined expression entry point.

To run the commands yourself after activating the installed CLI:

```sh
. .venv/bin/activate
gramson generate --manifest examples/bitwise/language.yaml --output-directory build/examples/bitwise
gramson validate examples/bitwise/expressions/nested.yaml --schema build/examples/bitwise/expression.schema.yaml
gramson validate examples/bitwise/expressions/nested.json --schema build/examples/bitwise/expression.schema.yaml
gramson validate examples/bitwise/expressions/conversions.yaml --schema build/examples/bitwise/expression.schema.yaml
gramson validate examples/bitwise/expressions/conversions.json --schema build/examples/bitwise/expression.schema.yaml
```

`expressions/invalid-arity.yaml` must fail with code `1` against this grammar:
`&` requires two arguments. The bundled core grammar rejects bitwise calls unless
you select the generated extension grammar with `--schema`.
`expressions/invalid-conversion-arity.yaml` also fails with code `1`, because
`hexToInt` needs one argument.

## Explicit hexadecimal conversions

```json
{"hexToInt": ["0xFF"]}
```

```json
{"intToHex": [255]}
```

Both operators accept one expression, including computed values such as
`{"hexToInt": {"var": "maskHex"}}`. Non-array shorthand is accepted; arrays
directly under an operator are its argument list.

The intended evaluation contract is:

- `hexToInt` accepts a string fully matching `-?(?:0[xX])?[0-9a-fA-F]+`. The prefix
  is optional, digits are ASCII and case-insensitive, and a minus sign precedes
  the optional prefix. Whitespace, a leading plus sign, missing digits, and
  non-string inputs are rejected.
- `intToHex` accepts an integer without implicit coercion of strings, booleans,
  or floats. It returns lowercase hexadecimal digits with a `0x` prefix, no
  redundant leading zeros, and a leading minus sign for negative integers.
  Intended results include `255` becoming `"0xff"`, `-255` becoming `"-0xff"`,
  and zero becoming `"0x0"`.

These are intended semantics, not implemented conversions. The generated schema
checks argument counts and recursive expression structure; it does not evaluate
operands or check their resulting types, hexadecimal contents, or conversion
results. For example, `{"hexToInt": ["not hexadecimal"]}` passes syntax
validation. JSON hexadecimal inputs must be quoted strings. In YAML, quote
`'0xFF'` to preserve it as a string; unquoted `0xFF` is parsed as a number.

## Names and collisions

These keys do not collide with core operators: `&` and `|` differ from `and` and
`or`, `~` differs from `!`, and `<<` and `>>` differ from `<` and `>`.
`hexToInt` and `intToHex` are also absent from core. All eight definition names
differ from core `schemaName` values. The composed language has 43 operator keys:
35 from core and eight from this extension.

Generation rejects duplicate operator keys or definition names across all
selected groups, including core. There are no implicit overrides.
Quote symbolic operator keys in YAML; in particular, unquoted `~` represents
null and unquoted `<<` has YAML merge-key meaning.

This extension defines syntax only. Bitwise operand coercion, integer precision,
bit width, signedness, shift-count handling, and evaluation remain unspecified.
It does not add these operators to JSON Logic's documented core or implement
an evaluator.
