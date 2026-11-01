# JSON Logic shared test corpus

`tests.json` is an unmodified, byte-for-byte snapshot of the shared JSON Logic
evaluation tests published at <https://jsonlogic.com/tests.json>. The
[JavaScript runner](https://github.com/jwadhams/json-logic-js/blob/master/tests/tests.js)
also consumes this corpus. Copyright (c) 2015 Jeremy Wadhams; distributed under
the upstream MIT license, reproduced verbatim in [LICENSE](LICENSE).

[snapshot.json](snapshot.json) records the retrieval date, immutable upstream
source URLs and commit revisions, SHA-256 checksums, and case count. The corpus
is pinned to the website repository's `gh-pages` revision; the project license
is pinned separately to its `master` revision. The downloaded website corpus
was verified byte-for-byte against that pinned GitHub source.

The array contains 278 test triples of `[expression, data, expected_result]`,
interspersed with string headings. Preserve all three fields and the headings.
Gramson currently checks only expression syntax; data and expected results are
retained for future evaluator tests. No upstream evaluator is vendored.

## Gramson compatibility

`tests/test_jsonlogic.py` runs offline as part of `make test` and `make check`.
It verifies the snapshot checksums and validates every expression. All 278
expressions are currently accepted, with no exclusions.

The currently empty exclusion list lives separately in
[`tests/jsonlogic_exclusions.json`](../../jsonlogic_exclusions.json).
Case numbers are one-based positions among test triples, ignoring string
headings. Every exclusion records the original expression and the reason for
rejection. Exclusions must still fail validation; all other cases must pass.
This measures acceptance of this corpus, not runtime equivalence or exhaustive
JSON Logic compatibility.

## Updating deliberately

1. Select an upstream commit and download `tests.json` from its immutable raw
   GitHub URL. Replace the whole file without reformatting or filtering it.
2. Review the diff and upstream license. Preserve the copyright and complete
   license notice; update the license snapshot if needed.
3. Update the revisions, source URLs, retrieval date, checksums, and case count
   in `snapshot.json`. Check the bytes with `shasum -a 256`.
4. Review every syntax rejection against the specification. Update the separate
   exclusion list and these counts only for intentional differences, recording
   each expression and reason. Do not generate exclusions automatically from
   whatever happens to fail.
5. Run `make check` and commit the snapshot, metadata, and expectations together.

Tests never download or refresh the corpus automatically.
