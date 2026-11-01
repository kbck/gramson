import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from schema_support import read_schemas, schema_registry

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "tests" / "vendor" / "jsonlogic"


def load_json(path):
    return json.loads(path.read_bytes())


class JSONLogicCorpusTests(unittest.TestCase):
    def test_snapshot_integrity(self):
        snapshot = load_json(VENDOR / "snapshot.json")
        for name in ("corpus", "license"):
            with self.subTest(file=name):
                record = snapshot[name]
                self.assertEqual(
                    hashlib.sha256((VENDOR / record["file"]).read_bytes()).hexdigest(),
                    record["sha256"],
                    "Vendored bytes changed; review and update the snapshot deliberately.",
                )

    def test_upstream_expression_syntax(self):
        items = load_json(VENDOR / "tests.json")
        self.assertIsInstance(items, list)
        cases = []
        for item in items:
            if isinstance(item, str):
                continue  # Upstream section headings are not test cases.
            self.assertIsInstance(item, list)
            self.assertEqual(len(item), 3, "Expected [expression, data, result].")
            cases.append(item)
        snapshot = load_json(VENDOR / "snapshot.json")
        self.assertEqual(len(cases), snapshot["corpus"]["case_count"])
        self.assertTrue(cases)

        exclusions = {}
        for exclusion in load_json(ROOT / "tests" / "jsonlogic_exclusions.json"):
            number = exclusion["case_number"]
            self.assertIs(type(number), int)
            self.assertTrue(1 <= number <= len(cases), "Stale exclusion case number.")
            self.assertNotIn(number, exclusions, "Duplicate exclusion case number.")
            self.assertIsInstance(exclusion["reason"], str)
            self.assertTrue(exclusion["reason"].strip())
            self.assertEqual(exclusion["expression"], cases[number - 1][0])
            exclusions[number] = exclusion

        schemas = read_schemas(ROOT / "schema")
        validator = Draft202012Validator({
            "$id": (ROOT / "schema" / "expression.schema.yaml").as_uri(),
            **schemas[Path("expression.schema.yaml")],
        }, registry=schema_registry(schemas, ROOT / "schema"))
        for number, (expression, _data, _result) in enumerate(cases, 1):
            with self.subTest(case_number=number, expression=expression):
                if number in exclusions:
                    self.assertFalse(
                        validator.is_valid(expression),
                        "Expected rejection changed: " + exclusions[number]["reason"],
                    )
                else:
                    validator.validate(expression)


if __name__ == "__main__":
    unittest.main()
