# Gramson operator specification

`spec/language.yaml`, the selected operator files, and
`gramson/generation.py` are the authoritative specification for expression
syntax. Core covers all 34 operators in the
[JSON Logic operations documentation](https://jsonlogic.com/operations.html).
It also includes the `?:` alias for `if`, giving 35 registered operator keys.
The generated Draft 2020-12 schemas are YAML. Edit the sources and regenerate;
do not edit generated schemas directly.

## Directories and manifest

```yaml
# spec/language.yaml
operatorDirectories:
  - core
```

Directories are relative to the manifest's directory. Only selected directories
are loaded, recursively including `.yaml` and `.yml` operator files. Sources are
sorted by path for deterministic output, independent of manifest directory order.
Missing or empty directories, repeated directory selections, paths outside the
specification, and malformed manifests are errors.

Installed Gramson also supports extending its bundled core declarations:

```yaml
include:
  - gramson:core
operatorDirectories:
  - custom
```

`include` is a list of unique bundled definition names. These declarations are
loaded from the installed package, combined with selected local files, and
compiled into one grammar. `operatorDirectories` may be omitted or empty when
`include` selects a bundled group; otherwise it must be a nonempty list.
Omitting `include`, or supplying an empty list, selects only local directories.
The repository's own manifest uses local `core` files so edits to those
declarations are reflected by `make generate`.

Select reusable optional extensions by name:

```yaml
include:
  - gramson:core
  - gramson:bitwise
```

The supported names are `gramson:core` and `gramson:bitwise`. The latter
selects `spec/extensions/bitwise.yaml` from the installed
package and emits `extensions/bitwise.schema.yaml`. Unknown names, repeated
selections, duplicate operator keys or definition names, and output-path
collisions with local groups are errors. Local and bundled output paths are
compared without case distinctions for portability.

`operatorDirectories` can be added to compose local groups with these bundled
declarations. Include only `gramson:bitwise` to select it without core.
Selecting local directories does not automatically enable any bundled group.

Bundled core groups are emitted under `core/`, and bitwise under `extensions/`.
Local files may share these directories when their output paths and definition
names do not collide. There is no precedence or override behavior: duplicate
operator keys, `schemaName` values, or output paths fail the whole generation
before files are written. Include-list order does not change the generated
grammar. Pin the Gramson package version for reproducible bundled definitions.

Core is split into `data.yaml`, `logic.yaml`, `comparison.yaml`,
`arithmetic.yaml`, `collection.yaml`, `string.yaml`, and `debugging.yaml`.
An additional folder can be enabled by adding it to `operatorDirectories`.
This composes syntax only; runtime extension loading and semantics remain open.

Each file contains a mapping of operator keys to definitions. Duplicate operator
keys or `schemaName` values across files are rejected with both source paths.
Duplicate YAML keys inside one file are also rejected; there are no implicit
overrides. Source files with the same relative base name but different YAML
extensions are rejected if they would generate the same output path.

## Define and generate

Each operator file, such as `spec/core/comparison.yaml`, defines syntax and arity:

```yaml
'>':
  schemaName: greaterThan
  title: Greater than
  summary: Compare whether the first value exceeds the second.
  argumentKind: expression
  minArgs: 2
  maxArgs: 2
```

This is an entry inside an operator-file mapping. `argumentKind` is either `string`
or recursive `expression`; it describes syntax, not evaluated operand types.
`minArgs` is required; omitting `maxArgs` allows an unbounded argument list.
`shorthand: true` also accepts a single unwrapped, non-array argument and requires
that one be an allowed arity. `var` accepts both `"price"` and `["price"]`.
Unsupported fields and malformed definitions produce an error.

`schemaName` gives each operator a readable, stable name under `$defs`, such as
`addition`, `greaterThan`, or `conditional`. Every shipped operator supplies one.
If omitted for an experimental entry, its name defaults to `operator_` followed
by the operator key. Names must be nonempty and unique, and cannot replace the
shared `expression`, `scalarLiteral`, or `arrayExpression` definitions.

`title`, `summary`, and `description` are optional documentation fields in the
generator; when supplied, each must be a nonblank string. The shipped specification
requires a title and summary for every operator through a test. Longer
descriptions are optional, so simple operators need no redundant paragraphs.
Experimental operators may omit all three; the default title is the operator
key followed by `expression`.

JSON Schema has standard `title` and `description` annotations but no standard
`summary` annotation. The generator uses `title` directly and joins the summary
and longer description, when present, into `description` as separate paragraphs.
This keeps both texts visible in schema viewers without a custom keyword.
Descriptions explain operator intent and syntax; they do not implement runtime
semantics or add validation constraints.

Expressions now include recursively validated arrays. An array directly under an
operator is always its argument list. To pass an array as one argument, wrap it:
`{"!!": [[]]}` has one empty-array operand, while `{"!!": []}` has no operands
and is rejected. Excluding arrays from the shorthand branch prevents overlapping
`oneOf` alternatives and stops extra arguments from being mistaken for shorthand.

## Accepted forms

All positions accept expressions. Names such as source, body, key, and offset
describe positional roles, not evaluated-type constraints.

| Operators | Argument positions / arity | Non-array shorthand |
| --- | --- | --- |
| `var` | Zero to two: key, optional default; zero means current context | Yes |
| `missing` | Zero or more keys, or one key-list expression | Yes |
| `missing_some` | Required count, key-list expression | No |
| `if`, `?:` | Zero or more: condition/result pairs, optional fallback | Yes |
| `and`, `or` | One or more expressions | Yes |
| `!`, `!!`, `log` | One expression | Yes |
| `==`, `===`, `!=`, `!==`, `>`, `>=` | Two expressions | No |
| `<`, `<=` | Two expressions, or three for a range | No |
| `+`, `*`, `min`, `max` | One or more expressions | Yes |
| `-` | One or two expressions | Yes |
| `/`, `%`, `in` | Two expressions | No |
| `map`, `filter` | Source, body | No |
| `reduce` | Source, body, optional initial value | No |
| `all`, `some`, `none` | Source, predicate | No |
| `merge`, `cat` | Zero or more expressions | Yes |
| `substr` | Source, offset, optional length | No |

`if` and its `?:` alias accept both even argument counts (pairs without a fallback) and odd counts
(pairs followed by a fallback). Every list of at least two expressions has one
of those shapes, so the registry needs no parity rule. Its agreed runtime rule
is to return `null` if no condition matches and no fallback is present, as in the
[JavaScript reference implementation](https://github.com/jwadhams/json-logic-js/blob/master/logic.js).
Tests validate the branch syntax only; no evaluation is performed.
Zero arguments are accepted (JSON Logic returns `null`). With one argument,
that expression is the fallback and is evaluated directly. Non-array shorthand
also supplies a single fallback expression, including a nested operator call.

Collection bodies and string arguments fit the existing expression-list model.
There is no need for separate positional type machinery while semantic typing
remains open. Such machinery can be considered when distinct static constraints
for particular positions are actually required.

## Compatibility boundaries

This is a deliberate syntax profile, not every input accepted by an interpreter:

- Arithmetic, logical lists, and extrema require the arities above;
  permissive empty calls, ignored extra arguments, and incomplete binary calls
  are not generally accepted. `var`, `missing`, `merge`, `cat`, `if`, and `?:`
  explicitly allow zero.
- Arrays are recursive expressions, not opaque JSON data. Unknown operators
  inside arrays, defaults, and branches are rejected even if not evaluated.
- Arbitrary object literals and custom runtime operators are outside this profile.
- Lookup, truthiness, coercion, equality, collection scope, short-circuiting,
  empty-collection results, and errors are not implemented or tested as runtime
  behavior. `log` is accepted syntax and does not print anything during validation.

## Generate and test

From the repository root, using the environment described in the main README:

```sh
.venv/bin/python tools/generate_schema.py
.venv/bin/python -m unittest discover -s tests -v
```

Generation uses PyYAML to read the operator sources and write generated schemas as
YAML. Tests use `jsonschema` and `PyYAML` from requirements-dev.txt; they parse
schemas before validation and read the hand-written OpenAPI document.

The repository script defaults to `spec/language.yaml` and output directory
`schema`. The installed command defaults to the bundled core language and
output directory `schema`:

```sh
gramson generate
```

Use a manifest to generate a custom or extended language:

```sh
gramson generate --manifest path/to/language.yaml --output-directory path/to/schema
gramson validate expression.yaml --schema path/to/schema/expression.schema.yaml
```

`--schema` selects a local generated entry point. The containing output directory
must retain the generated relative layout; references stay within that directory,
and no installed core schema or remote retrieval is used. JSON and YAML entry-point files are supported. Schema-loading
or unresolved-reference errors exit with code `2`; invalid expressions exit with
code `1`. Both core and custom operands recurse through the composed entry point.

All sources are loaded and validated before output is written. Freshness tests
cover every generated file. Generation preserves hand-written files and does
not delete unreferenced old outputs; removed groups disappear from the root
grammar and therefore cannot be used as expressions through that entry point.

The [Swagger viewer guide](../docs/README.md) explains how to browse the request
and response through the placeholder `POST /evaluate` specification. Its only
schema components are external references to `expression` and `jsonValue`;
operator definitions remain in the separate expression schema. There is no
evaluation service, and the viewer disables request execution.

`docs/openapi.yaml` is maintained directly: operator changes need no wrapper
edits because it references the root schema. `docs/json-value.schema.yaml`
reuses `../schema/shared.schema.yaml#/$defs/scalarLiteral`, while defining its own
recursive arrays and objects as result data.

## Generated grammar

Source directories and file base names are mirrored:

```text
spec/core/arithmetic.yaml       -> schema/core/arithmetic.schema.yaml
spec/core/logic.yaml            -> schema/core/logic.schema.yaml
spec/extras/nested/custom.yaml  -> schema/extras/nested/custom.schema.yaml
```

Each grouped schema contains named operator `$defs`, preserving documentation,
arity, and shorthand constraints. `schema/expression.schema.yaml` is the single
language entry point. Its `expression` alternatives reference shared scalars,
recursive arrays, and each enabled operator in its grouped file.

Recursive operands in grouped files reference the root's `expression`
definition using a relative path. This allows core operators to contain
extension expressions and extensions to contain core expressions. Arrays recurse
through the same language entry point. References escape file paths and JSON
Pointer tokens where necessary.

`schema/shared.schema.yaml` owns the shared `scalarLiteral` definition. Both
the language entry point and the hand-written JSON-value schema reference it;
result containers remain independent of expression containers.

The generator still owns the available argument kinds and translation rules.
Heterogeneous positional constraints would need more design if introduced.
Typing, conversions, named constants, evaluation, and runtime extensions remain
open questions. Accepted and rejected examples live in `examples/valid.json`
and `examples/invalid.json`. Tests cover generation freshness, operator
coverage, arity, metadata, composition, collisions, and external references.
