# Scope and design decisions

## Scope and decisions


- Accept JSON scalar literals and recursive arrays of expressions.
- Represent each operation as a closed object with exactly one registered key.
- Support data access, conditionals, Boolean logic, comparisons, arithmetic,
  collections, strings, and logging syntax.
- Accept variable defaults, numeric and computed keys, unary shorthand, and
  the documented arity profile.
- Reject unknown operators and arbitrary object literals throughout expressions,
  including inside arrays, defaults, and unselected branches.

This specifies structural acceptance. It does not implement evaluation or
semantic typing. For example, `{"+": [true, "2", null]}` and
`{"map": [true, "body"]}` pass syntax validation without promising meaningful
evaluation. The profile constrains arities rather than accepting every malformed
call that a permissive interpreter might process.

`if` and its `?:` alias accept condition/result pairs with an optional final fallback. The agreed
runtime result is `null` when no condition matches and no fallback is supplied;
there is no evaluator yet to execute that rule.
Empty argument lists are accepted and yield `null` in JSON Logic. A single
argument is a fallback expression; non-array shorthand is also accepted.

Results are data rather than expressions. The hand-written
[JSON-value schema](json-value.schema.yaml) accepts scalars, recursive
arrays, and arbitrary objects. It reuses `scalarLiteral` from the generated shared schema
but defines its own recursive containers so result objects are never treated as
operator calls.

## Open design questions


- **Semantic typing:** Should a separate phase check operand and result types?
  How would it learn variable types and handle null or missing values?
- **Explicit conversions:** This remains the preferred direction. Unary `+` and
  `!!` are accepted syntax, but conversion failures and implicit coercions
  remain undecided.
- **Named constants:** Are they needed, and how should they be represented,
  scoped, and distinguished from external data?
- **Custom operator extensions:** The registry describes build-time syntax.
  Runtime operator registration, scoping, and versioning remain unspecified.
- **Evaluation and compatibility:** Lookup, truthiness, arithmetic, equality,
  collection scope, short-circuiting, and errors require decisions. The
  no-fallback `if` result is settled as `null`.

## Next steps


Settle semantic typing, conversions, and runtime compatibility before building
an evaluator. For each syntax change, update the relevant operator file, regenerate the
schemas, and add accepted and rejected examples.

