import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from schema_support import read_schemas, schema_registry

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ExpressionSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schemas = read_schemas(ROOT / "schema")
        cls.schema = schemas[Path("expression.schema.yaml")]
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator({
            "$id": (ROOT / "schema" / "expression.schema.yaml").as_uri(),
            **cls.schema,
        }, registry=schema_registry(schemas, ROOT / "schema"))

    def test_valid_examples(self):
        examples = load_json(ROOT / "examples" / "valid.json")
        self.assertTrue(examples, "The valid example corpus must not be empty.")
        for example in examples:
            with self.subTest(name=example["name"]):
                self.validator.validate(example["expression"])

    def test_invalid_examples(self):
        examples = load_json(ROOT / "examples" / "invalid.json")
        self.assertTrue(examples, "The invalid example corpus must not be empty.")
        for example in examples:
            with self.subTest(name=example["name"]):
                self.assertFalse(
                    self.validator.is_valid(example["expression"]),
                    example["reason"],
                )


if __name__ == "__main__":
    unittest.main()
