# Gramson schema viewer

This is a documentation-only OpenAPI 3.1 wrapper around the generated grammar.
The proposed `POST /evaluate` accepts an `expression` and optional JSON `data`
context. Its proposed 200 response is a raw JSON value: a scalar, recursive
array, or object, without a result envelope. No evaluator or HTTP handler exists.
The 200 contract and listed 501 response are documentation, not running endpoints.

## View locally

From the repository root:

```sh
make setup
make serve
```

`make serve` generates the schemas and serves the repository root. Use
`make lint-openapi` to validate the wrapper and its external references, or
`make check` to also run all tests. Override the port with `make serve PORT=8000`.
Open [the local viewer](http://127.0.0.1:8765/docs/). Expand **POST /evaluate** to
inspect the request and response. Under **Schemas**, `expression` and `jsonValue`
reference the two external schemas. Operator documentation and named definitions
remain inside the expression schema. Stop the server with Ctrl+C.

The viewer loads Swagger UI 5 JavaScript and CSS from the unpkg CDN, so an
internet connection is required. All specification files remain local. Serve
the repository root so the browser can fetch both the YAML wrapper and the
expression entry point, grouped operators, shared definitions, and JSON-value schema. Opening `index.html` directly as a file is not
supported.

Execution is disabled with `supportedSubmitMethods: []`. The online validator is
disabled with `validatorUrl: null`; the viewer is for reading the specification.
These settings follow the [Swagger UI configuration documentation](https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/).

## Hand-written wrapper

`openapi.yaml` is a hand-written wrapper around the standalone Draft 2020-12
schema at `../schema/expression.schema.yaml`. Its named
`components.schemas` entries contain external references, not copied grammar.
For example:

```yaml
components:
  schemas:
    expression:
      $ref: ../schema/expression.schema.yaml
    jsonValue:
      $ref: ./json-value.schema.yaml
```

The generated expression entry point references named operator definitions in
`schema/core/*.schema.yaml` and shared literals in `schema/shared.schema.yaml`.
Grouped files mirror the selected operator-source directories and base names.
Their recursive operands reference the root language, so they accept expressions
from any enabled group. References remain relative to their containing files. The separate hand-written `docs/json-value.schema.yaml` defines result
data with named `jsonValue`, `arrayValue`, and `objectValue` definitions. Its
scalar alternative references `../schema/shared.schema.yaml#/$defs/scalarLiteral` instead of repeating the scalar types. Its arrays and object property
values recurse through `jsonValue`; `arrayExpression` cannot be reused here
because result arrays may contain arbitrary objects rather than expressions.

The 200 response references `jsonValue`, not `expression`. Result objects have
arbitrary keys and are never interpreted as operator calls, including objects
such as `{"unknown": [1]}` or `{"+": []}`. Both are valid result data even though
they fail expression validation. Object literals remain outside the expression
grammar; a future evaluator can still return objects obtained from input data.
Response examples cover scalars, null, nested arrays, and objects. They illustrate
the response format, not tested evaluation results.

Other viewers must be able to fetch all referenced files with their relative layout
preserved; importing the YAML alone into a disconnected editor is insufficient.

The wrapper uses the default OpenAPI 3.1 schema dialect, which incorporates
Draft 2020-12, for compatibility with Swagger UI. The standalone schema keeps
its explicit Draft 2020-12 declaration. See the
[OpenAPI 3.1 Schema Object specification](https://spec.openapis.org/oas/v3.1.1.html#schema-object).

The wrapper exposes only `expression` and `jsonValue`. Individual operators and
shared expression nodes remain named `$defs` in the external grouped YAML schemas and
are reached through its references. There are no per-operator OpenAPI aliases
or OpenAPI-specific restrictions on their definition names.

Change operator documentation in `spec/core/*.yaml` (or another selected
source directory) and regenerate the expression schemas. The
`spec/language.yaml` manifest selects enabled directories. Edit `openapi.yaml` directly when the API contract changes;
operator changes require no edits because the references remain the same.
The JSON-value schema is also hand-written and uses the shared scalar definition.
Tests check generated expression-schema freshness, metadata, and request/response
validation through the external references. Neither hand-written file has a
generation or freshness-comparison step.
