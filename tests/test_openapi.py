import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from jsonschema import Draft202012Validator
from referencing import Resource

from schema_support import read_schemas, schema_registry
from tools.generate_schema import generate_schemas, load_language

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class OpenAPIViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schemas = read_schemas(ROOT / "schema")
        cls.schema = schemas[Path("expression.schema.yaml")]
        cls.document = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text(encoding="utf-8"))
        cls.json_value_schema = load_yaml(ROOT / "docs" / "json-value.schema.yaml")
        Draft202012Validator.check_schema(cls.json_value_schema)
        cls.request_path = "#/paths/~1evaluate/post/requestBody/content/application~1json/schema"
        registry = schema_registry(schemas, ROOT / "schema").with_resource(
            (ROOT / "docs" / "json-value.schema.yaml").as_uri(),
            Resource.from_contents(cls.json_value_schema),
        )
        cls.validator = Draft202012Validator({
            "$id": (ROOT / "docs" / "openapi.yaml").as_uri(),
            "$ref": cls.request_path, **cls.document,
        }, registry=registry)
        cls.response_validator = Draft202012Validator({
            "$id": (ROOT / "docs" / "openapi.yaml").as_uri(),
            "$ref": "#/paths/~1evaluate/post/responses/200/content/application~1json/schema",
            **cls.document,
        }, registry=registry)

    def test_schema_components_reference_external_definitions(self):
        self.assertEqual(self.document["components"]["schemas"], {
            "expression": {"$ref": "../schema/expression.schema.yaml"},
            "jsonValue": {"$ref": "./json-value.schema.yaml"},
        })

    def test_cli_generates_expression_schema(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            subprocess.run([
                sys.executable, str(ROOT / "tools" / "generate_schema.py"),
                "--output-directory", str(directory),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(
                read_schemas(directory),
                generate_schemas(load_language(ROOT / "spec" / "language.yaml")),
            )

    def test_json_values_reuse_the_generated_scalar_definition(self):
        self.assertNotIn("scalarLiteral", self.json_value_schema["$defs"])
        self.assertIn(
            {"$ref": "../schema/shared.schema.yaml#/$defs/scalarLiteral"},
            self.json_value_schema["$defs"]["jsonValue"]["oneOf"],
        )

    def test_request_references_preserve_expression_validation(self):
        for filename, expected in (
            ("valid.json", True), ("invalid.json", False),
        ):
            for example in load_json(ROOT / "examples" / filename):
                with self.subTest(collection=filename, name=example["name"]):
                    self.assertEqual(
                        self.validator.is_valid({"expression": example["expression"]}),
                        expected,
                    )

    def test_request_envelope_and_example(self):
        operation = self.document["paths"]["/evaluate"]["post"]
        self.validator.validate(operation["requestBody"]["content"]["application/json"]["example"])
        for data in (None, True, 42, "text", [], [1], {}, {"age": 21}):
            with self.subTest(data=data):
                self.validator.validate({"expression": None, "data": data})
        for request in ({}, {"data": {}}, {"expression": 1, "unexpected": 0}, []):
            with self.subTest(request=request):
                self.assertFalse(self.validator.is_valid(request))

    def test_wrapper_is_documentation_only(self):
        self.assertEqual(self.document["openapi"], "3.1.1")
        self.assertNotIn("jsonSchemaDialect", self.document)
        self.assertEqual(set(self.document["paths"]), {"/evaluate"})
        operation = self.document["paths"]["/evaluate"]["post"]
        self.assertEqual(set(operation["responses"]), {"200", "501"})

    def test_response_accepts_recursive_json_values(self):
        values = [
            None, True, False, 0, -1.5, "", "adult", [], {},
            [1, None, {"name": "Ada", "nested": [[False]]}],
            {"user": {"name": "Ada"}, "scores": [1, 2]},
            {"unknown": [1]}, {"+": []},
        ]
        for value in values:
            with self.subTest(value=value):
                self.response_validator.validate(value)
        examples = self.document["paths"]["/evaluate"]["post"]["responses"]["200"]["content"]["application/json"]["examples"]
        for name, example in examples.items():
            with self.subTest(example=name):
                self.response_validator.validate(example["value"])

    def test_result_objects_are_not_parsed_as_expressions(self):
        for value in ({"unknown": [1]}, {"+": []}, {"name": "Ada"}):
            with self.subTest(value=value):
                self.assertTrue(self.response_validator.is_valid(value))
                self.assertFalse(self.validator.is_valid({"expression": value}))

    def test_response_rejects_non_json_python_values_recursively(self):
        for value in (b"bytes", {1, 2}, (1, 2), [b"bytes"], {"nested": {1, 2}}):
            with self.subTest(value=value):
                self.assertFalse(self.response_validator.is_valid(value))


if __name__ == "__main__":
    unittest.main()
