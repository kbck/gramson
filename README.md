# Gramson

**Define operators once. Generate the grammar that validates your JSON expressions.**

Adding operators to a JSON expression language means keeping its syntax rules
and validation in sync. Gramson compiles YAML operator declarations into a
recursive JSON Schema grammar, so adding an operator or changing its arguments
doesn't require hand-editing the validation schema.

## Why Gramson?

JSON Schema can already validate recursive expressions. Gramson generates the
operator objects, argument-count constraints, shorthand forms, and references
from your declarations. JSON Logic supplies the bundled starting profile;
you can extend it or define an independent language.

**Operator libraries become composable grammar modules.** Include groups from
different libraries, and their operators can nest inside one another. The
combined grammar is generated from the selected definitions and works with
standard Draft 2020-12 JSON Schema validators.

Gramson is a Python library and CLI. It defines and validates syntax; it does
not evaluate expressions.

## Example

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

## Try it

Requires Python 3.10 or newer. Install in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install gramson
```

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
  forms. See the [bitwise example](examples/bitwise/README.md).
- **Your libraries:** include names such as `mystuff:myops` with explicit
  `--spec-path` search roots. See the [external library example](examples/external/README.md).

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
