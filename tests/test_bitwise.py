import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gramson.cli import expression_validator
from gramson.generation import generate_schemas, load_core, load_language, merge_operators, read_yaml, write_schemas


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "bitwise"
BINARY = ("&", "|", "^", "<<", ">>")


class BitwiseExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.groups = load_language(EXAMPLE / "language.yaml")
        output = Path(temporary.name)
        write_schemas(generate_schemas(cls.groups), output)
        cls.validator = expression_validator(output / "expression.schema.yaml")

    def test_operator_keys_and_definition_names_do_not_collide_with_core(self):
        core = merge_operators(load_core())
        combined = merge_operators(self.groups)
        added = set(combined) - set(core)
        self.assertEqual(added, {*BINARY, "~"})
        self.assertEqual(len(combined), 41)
        self.assertEqual({name: combined[name] for name in core}, core)
        core_names = {definition["schemaName"] for definition in core.values()}
        extension_names = {combined[name]["schemaName"] for name in added}
        self.assertTrue(core_names.isdisjoint(extension_names))

    def test_binary_and_unary_argument_counts(self):
        for name in (*BINARY, "~"):
            for count in range(4):
                with self.subTest(operator=name, count=count):
                    expected = count == (1 if name == "~" else 2)
                    self.assertEqual(self.validator.is_valid({name: [1] * count}), expected)
            with self.subTest(operator=name, form="shorthand"):
                self.assertEqual(self.validator.is_valid({name: 1}), name == "~")
            with self.subTest(operator=name, form="extra property"):
                self.assertFalse(self.validator.is_valid({name: [1, 2], "extra": 0}))
        self.validator.validate({"~": {"var": "mask"}})
        self.assertFalse(self.validator.is_valid({"&": [1, {"unknown": []}]}))

    def test_json_and_yaml_examples_compose_all_six_operators(self):
        json_expression = json.loads((EXAMPLE / "expressions/nested.json").read_text())
        yaml_expression = read_yaml(EXAMPLE / "expressions/nested.yaml")
        self.assertEqual(json_expression, yaml_expression)
        self.validator.validate(json_expression)
        self.assertFalse(expression_validator().is_valid(json_expression))
        self.assertFalse(self.validator.is_valid(read_yaml(EXAMPLE / "expressions/invalid-arity.yaml")))


if __name__ == "__main__":
    unittest.main()
