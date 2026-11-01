# Include an external specification library

This ready-to-run example combines bundled `gramson:core` with a user-owned
`mystuff:myops` group. From the repository or unpacked source-distribution root:

```sh
make setup
make example-external
```

Both the JSON and YAML expressions should print `valid expression`. The generated
grammar goes into the ignored `build/examples/external/` directory.

## Layout

```text
examples/external/
  language.yaml
  vendor/                         # --spec-path points here
    mystuff/                      # namespace
      myops/                      # group
        wrapping.yaml             # operator declarations
  expressions/
    nested.json
    nested.yaml
    invalid-arity.yaml
```

The manifest contains:

```yaml
include:
  - gramson:core
  - mystuff:myops
```

After activating the environment created by `make setup`, run the steps directly:

```sh
. .venv/bin/activate
gramson generate --manifest examples/external/language.yaml --spec-path examples/external/vendor --output-directory build/examples/external
gramson validate examples/external/expressions/nested.yaml --schema build/examples/external/expression.schema.yaml
gramson validate examples/external/expressions/nested.json --schema build/examples/external/expression.schema.yaml
```

`mystuff:myops` resolves to the directory `<spec-path>/mystuff/myops/`. Its YAML
operator files are loaded recursively and emitted under
`mystuff/myops/*.schema.yaml`. The example's `wrap` operator takes exactly one
recursive expression. The nested examples combine it with core `+` and `var`.
`invalid-arity.yaml` must fail validation with exit code `1`.

## Resolution rules

- Repeat `--spec-path` to search multiple libraries. Relative search paths are
  relative to the command's working directory, not to the manifest.
- Namespace and group identifiers start with a lowercase ASCII letter and then
  contain lowercase letters, digits, underscores, or hyphens. Each include has
  exactly one colon, such as `mystuff:myops`.
- External groups are directories containing `.yaml` or `.yml` operator
  declarations, not manifests. Group directories and operator files must stay
  within their selected source tree. No package discovery or downloads occur.
- `gramson:` is reserved for bundled definitions. Search paths cannot override
  `gramson:core` or supply new `gramson:` groups.
- If multiple distinct search roots contain the same include, generation fails
  with an ambiguity error listing the matches. Search-path order gives no
  precedence. Repeating the same resolved search root is harmless.
- Namespaces identify specification groups; operator keys are not automatically
  prefixed. This example defines `wrap`, not `mystuff:wrap`. Duplicate operator
  keys, definition names, and output paths still fail generation.

Once generated, move or distribute the whole schema directory together.
Validation needs only those schemas; it does not need the original library or
search paths. These declarations describe syntax, not an evaluator.
