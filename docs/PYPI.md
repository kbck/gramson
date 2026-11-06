# Gramson

**Define operators once. Generate the grammar that validates your JSON expressions.**

Gramson compiles YAML operator declarations into recursive JSON Schema grammars.
Extend the bundled JSON Logic syntax profile with your application's operators,
or define an independent language. Its Python library and CLI generate schemas
and validate JSON or YAML expressions; your application supplies evaluation.

## Install and validate

Requires Python 3.10 or newer. Install in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install gramson
```

Validate a core expression immediately:

```sh
printf '%s\n' '{">=": [{"var": "age"}, 18]}' | gramson validate -
```

For a saved rule, use `gramson validate expression.json` or
`gramson validate expression.yaml`. Validation checks syntax, without evaluating
the rule or requiring its input data. Without `--schema`, it uses the bundled
core grammar.

## Extend the language with a host operator

Suppose your application stores loan eligibility rules as JSON. An illustrative
rule requires a credit score of at least 700 and monthly debt payments no greater
than 35% of gross monthly income.

Core operators handle the comparisons and arithmetic. Your application adds
`creditScore`, which looks up an applicant's score in the host system. Save its
syntax declaration in `language/custom/credit.yaml`:

```yaml
creditScore:
  argumentKind: expression
  minArgs: 1
  maxArgs: 1
```

Save the following rule in `rules/eligibility.json`. It combines `creditScore`
with core comparisons and arithmetic:

```json
{
  "and": [
    {">=": [{"creditScore": [{"var": "applicant.id"}]}, 700]},
    {"<=": [
      {"/": [
        {"var": "monthlyDebtPayments"},
        {"var": "grossMonthlyIncome"}
      ]},
      0.35
    ]}
  ]
}
```

The caller supplies the applicant ID, monthly debt payments, and gross monthly
income. During evaluation, `creditScore` fetches the score from the host system.

**Gramson checks the rule's structure before you save or run it**, catching
unknown operators, missing arguments, and malformed nested expressions. For
example, it rejects `{"creditScore": []}` (missing an applicant) and
`{"creditScore": [{"vra": "applicant.id"}]}` (a misspelled nested operator).
Add more host operators and regenerate; the validation schema stays in sync.

Your application evaluates the rule, implements the lookup, and handles runtime
checks such as nonzero income. Gramson generates the grammar.

Create a project folder with this structure. Save the declaration above in
`language/custom/credit.yaml` and the JSON rule in `rules/eligibility.json`:

```text
loan-example/
├── language/
│   ├── language.yaml
│   └── custom/
│       └── credit.yaml
└── rules/
    └── eligibility.json
```

Put this manifest in `language/language.yaml`:

```yaml
include:
  - gramson:core
operatorDirectories:
  - custom
```

From inside `loan-example/`, generate the combined grammar, then validate your rule:

```sh
gramson generate --manifest language/language.yaml --output-directory generated
gramson validate rules/eligibility.json --schema generated/expression.schema.yaml
```

The validation command prints `rules/eligibility.json: valid expression`.
Generated output includes core and custom schemas, shared definitions, and one
expression entry point. Keep the directory together when moving it; validation
uses these files offline, without needing the source declarations.

## Compose operator libraries

Select bundled extensions in your manifest:

```yaml
include:
  - gramson:core
  - gramson:bitwise
```

The bundled bitwise group adds `&`, `|`, `^`, `~`, `<<`, `>>`, `hexToInt`, and
`intToHex`. Add `operatorDirectories` to combine these with local declarations.
Include only `gramson:bitwise` to select it without core.

For a user-owned library, include its namespace and group:

```yaml
include:
  - gramson:core
  - mystuff:myops
```

```sh
gramson generate --manifest language.yaml --spec-path ./vendor --output-directory generated
```

This reads declarations from `vendor/mystuff/myops/` recursively. Repeat
`--spec-path` for multiple search roots. Generated schemas validate without the
source library. See the
[external library example](https://github.com/kbck/gramson/tree/main/examples/external).

Without `include`, a manifest selects only local directories. Include order gives
no precedence: duplicate operator keys, definition names, or output paths fail
generation. Pin the Gramson version for reproducible bundled declarations.

## Input formats and exit codes

Files ending in `.yaml` or `.yml` are read as YAML; other files and stdin default
to JSON. Use `--format json` or `--format yaml` to override detection. Each input
contains one expression, without an API request envelope. YAML values must be
representable as JSON: duplicate or non-string keys, non-finite numbers,
timestamps, and cyclic aliases are rejected. Quote dates to use them as strings.

Exit codes are `0` for valid syntax, `1` for an invalid expression, and `2` for
input, schema, or command usage errors. `python -m gramson validate ...` is also
supported. See the
[usage guide](https://github.com/kbck/gramson/blob/main/docs/USAGE.md) for details.

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

See the [project overview](https://github.com/kbck/gramson#readme),
[operator specification](https://github.com/kbck/gramson/blob/main/spec/README.md),
and [issue tracker](https://github.com/kbck/gramson/issues).

## License and acknowledgements

Gramson is licensed under MIT. Its included expression language builds on
[JSON Logic](https://jsonlogic.com/), created by Jeremy Wadhams. The vendored
upstream tests retain their original MIT license and attribution; see the
[third-party notices](https://github.com/kbck/gramson/blob/main/THIRD_PARTY_NOTICES.md).
