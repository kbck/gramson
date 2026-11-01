from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
import yaml

from tools.generate_schema import generate_schema, generate_schemas, load_language, merge_operators


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = load_language(ROOT / "spec" / "language.yaml")
        cls.operators = merge_operators(cls.groups)
        cls.generated = generate_schema(cls.operators)
        Draft202012Validator.check_schema(cls.generated)
        cls.validator = Draft202012Validator(cls.generated)

    def test_every_operator_has_a_valid_example(self):
        covered = set()

        def visit(expression):
            if isinstance(expression, list):
                for item in expression:
                    visit(item)
            elif isinstance(expression, dict):
                covered.update(expression)
                for value in expression.values():
                    visit(value)

        for example in load_json(ROOT / "examples" / "valid.json"):
            visit(example["expression"])
        self.assertEqual(covered, set(self.operators))

    def test_operator_arities_and_shorthand(self):
        groups = [
            (("==", "===", "!=", "!==", ">", ">=", "/", "%", "in",
              "missing_some", "map", "filter", "all", "some", "none"), 2, 2, False),
            (("!", "!!", "log"), 1, 1, True),
            (("<", "<=", "substr", "reduce"), 2, 3, False),
            (("-",), 1, 2, True),
            (("+", "*", "min", "max", "and", "or"), 1, None, True),
            (("var",), 0, 2, True),
            (("merge", "cat", "missing", "if", "?:"), 0, None, True),
        ]
        tested = set()
        for names, minimum, maximum, shorthand in groups:
            for name in names:
                tested.add(name)
                counts = {0, 1, minimum, minimum + 1, 8}
                if maximum is not None:
                    counts.update((maximum, maximum + 1))
                for count in counts:
                    with self.subTest(operator=name, arguments=count):
                        expected = count >= minimum and (
                            maximum is None or count <= maximum
                        )
                        self.assertEqual(
                            self.validator.is_valid({name: [None] * count}), expected
                        )
                with self.subTest(operator=name, form="shorthand"):
                    self.assertEqual(self.validator.is_valid({name: None}), shorthand)
                with self.subTest(operator=name, form="extra property"):
                    self.assertFalse(
                        self.validator.is_valid({name: [None] * minimum, "extra": 0})
                    )
        self.assertEqual(tested, set(self.operators))

    def test_unary_array_operands_need_wrapping(self):
        for name in ("!", "!!", "log"):
            with self.subTest(operator=name):
                self.assertFalse(self.validator.is_valid({name: []}))
                self.assertTrue(self.validator.is_valid({name: [[]]}))
                self.assertFalse(self.validator.is_valid({name: [1, 2]}))
                self.assertTrue(self.validator.is_valid({name: [[1, 2]]}))

    def test_string_argument_kind_still_restricts_syntax(self):
        validator = Draft202012Validator(generate_schema({
            "lookup": {
                "argumentKind": "string", "minArgs": 1, "maxArgs": 1,
                "shorthand": True,
            }
        }))
        self.assertTrue(validator.is_valid({"lookup": "name"}))
        self.assertTrue(validator.is_valid({"lookup": ["name"]}))
        self.assertFalse(validator.is_valid({"lookup": 0}))
        self.assertFalse(validator.is_valid({"lookup": [["name"]]}))

    def test_generated_artifact_is_current(self):
        for relative, schema in generate_schemas(self.groups).items():
            with self.subTest(schema=str(relative)):
                Draft202012Validator.check_schema(schema)
                self.assertEqual(
                    load_yaml(ROOT / "schema" / relative), schema,
                    "Run tools/generate_schema.py after editing the specification.",
                )

    def test_shipped_operators_have_titles_and_summaries(self):
        for name, definition in self.operators.items():
            with self.subTest(operator=name):
                self.assertTrue(definition["title"].strip())
                self.assertTrue(definition["summary"].strip())
                generated = self.generated["$defs"][definition["schemaName"]]
                self.assertEqual(generated["title"], definition["title"])
                self.assertTrue(generated["description"].startswith(definition["summary"]))

    def test_optional_documentation_fields(self):
        cases = [
            ({}, "custom expression", None),
            ({"title": "Custom title"}, "Custom title", None),
            ({"summary": "A summary."}, "custom expression", "A summary."),
            ({"description": "Long details."}, "custom expression", "Long details."),
            (
                {"title": "Custom", "summary": "Brief.", "description": "Details."},
                "Custom", "Brief.\n\nDetails.",
            ),
        ]
        for metadata, title, description in cases:
            with self.subTest(metadata=metadata):
                schema = generate_schema({"custom": {
                    "argumentKind": "expression", "minArgs": 1, **metadata,
                }})
                Draft202012Validator.check_schema(schema)
                generated = schema["$defs"]["operator_custom"]
                self.assertEqual(generated["title"], title)
                self.assertEqual(generated.get("description"), description)

    def test_invalid_documentation_fields_are_rejected(self):
        for field in ("title", "summary", "description"):
            for value in (None, "", "  ", 1, [], {}):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        generate_schema({"custom": {
                            "argumentKind": "expression", "minArgs": 1, field: value,
                        }})

    def test_each_operator_has_a_named_definition(self):
        definitions = self.generated["$defs"]
        expected_names = {"expression", "scalarLiteral", "arrayExpression"}
        expected_references = [
            {"$ref": "#/$defs/scalarLiteral"},
            {"$ref": "#/$defs/arrayExpression"},
        ]
        for name, operator in self.operators.items():
            schema_name = operator["schemaName"]
            expected_names.add(schema_name)
            expected_references.append({"$ref": f"#/$defs/{schema_name}"})
            with self.subTest(operator=name):
                self.assertEqual(definitions[schema_name]["required"], [name])
                self.assertEqual(set(definitions[schema_name]["properties"]), {name})
        self.assertEqual(set(definitions), expected_names)
        self.assertEqual(definitions["expression"]["oneOf"], expected_references)

    def test_definition_names_resolve_with_special_characters(self):
        for name in ("a/b~c #é%", "expression"):
            for schema_name in (None, "named/a~b #é%"):
                with self.subTest(operator=name, schema_name=schema_name):
                    definition = {
                        "argumentKind": "expression", "minArgs": 1, "maxArgs": 1
                    }
                    if schema_name is not None:
                        definition["schemaName"] = schema_name
                    schema = generate_schema({name: definition})
                    Draft202012Validator.check_schema(schema)
                    validator = Draft202012Validator(schema)
                    self.assertTrue(validator.is_valid({name: [{name: [1]}]}))
                    self.assertFalse(validator.is_valid({name: [1, 2]}))

    def test_invalid_definition_names_are_rejected(self):
        for schema_name in ("", None, 1, "expression", "scalarLiteral", "arrayExpression"):
            with self.subTest(schema_name=schema_name):
                with self.assertRaises(ValueError):
                    generate_schema({"custom": {
                        "schemaName": schema_name,
                        "argumentKind": "expression", "minArgs": 1,
                    }})
        with self.assertRaises(ValueError):
            generate_schema({
                "first": {"schemaName": "shared", "argumentKind": "expression", "minArgs": 1},
                "second": {"schemaName": "shared", "argumentKind": "expression", "minArgs": 1},
            })

    def test_arity_change_requires_only_registry_edit(self):
        operators = deepcopy(self.operators)
        operators[">"]["minArgs"] = 3
        operators[">"]["maxArgs"] = 3
        validator = Draft202012Validator(generate_schema(operators))
        self.assertFalse(validator.is_valid({">": [3, 2]}))
        self.assertTrue(validator.is_valid({">": [3, 2, 1]}))
        self.assertFalse(validator.is_valid({">": [4, 3, 2, 1]}))
        self.assertFalse(validator.is_valid({"+": [0, {">": [3, 2]}]}))
        self.assertTrue(validator.is_valid({"+": [0, {">": [3, 2, 1]}]}))
        self.assertFalse(self.validator.is_valid({">": [3, 2, 1]}))

    def test_operator_addition_requires_only_registry_edit(self):
        operators = deepcopy(self.operators)
        operators["custom"] = {
            "argumentKind": "expression", "minArgs": 2, "maxArgs": 2
        }
        validator = Draft202012Validator(generate_schema(operators))
        expression = {">": [{"custom": [{"var": "price"}, 1]}, 0]}
        self.assertTrue(validator.is_valid(expression))
        self.assertFalse(validator.is_valid({"custom": [1]}))
        self.assertFalse(validator.is_valid({"custom": [3, 2, 1]}))
        self.assertFalse(validator.is_valid({"custom": [2, 1], "extra": 0}))
        self.assertFalse(self.validator.is_valid(expression))

    def test_malformed_registries_are_rejected(self):
        invalid_registries = [
            {},
            [],
            {"": {"argumentKind": "expression", "minArgs": 2}},
            {"+": []},
            {"+": {"argumentKind": "number", "minArgs": 2}},
            {"+": {"argumentKind": "expression"}},
            {"+": {"argumentKind": "expression", "minArgs": True}},
            {"+": {"argumentKind": "expression", "minArgs": -1}},
            {"+": {"argumentKind": "expression", "minArgs": 2, "maxArgs": 1}},
            {"+": {"argumentKind": "expression", "minArgs": 2, "maxArgs": None}},
            {"+": {"argumentKind": "expression", "minArgs": 2, "shorthand": "yes"}},
            {"+": {"argumentKind": "expression", "minArgs": 2, "shorthand": True}},
            {"+": {"argumentKind": "expression", "minArgs": 2, "typo": 1}},
            {"+": {"argumentKind": "expression", "minArgs": 0, "maxArgs": 0, "shorthand": True}},
        ]
        for registry in invalid_registries:
            with self.subTest(registry=registry):
                with self.assertRaises(ValueError):
                    generate_schema(registry)


if __name__ == "__main__":
    unittest.main()
