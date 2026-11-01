import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from jsonschema import Draft202012Validator

from gramson.generation import load_core, merge_operators
from schema_support import schema_registry
from tools.generate_schema import generate_schemas, load_language

ROOT = Path(__file__).resolve().parents[1]


class LanguageCompositionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.manifest = self.directory / "language.yaml"
        self.write("language.yaml", {"operatorDirectories": ["core"]})
        self.write("core/math.yaml", {"plus": {
            "schemaName": "addition", "argumentKind": "expression", "minArgs": 2,
        }})

    def write(self, relative, value):
        path = self.directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    def validator(self, schemas):
        output = self.directory / "output"
        return Draft202012Validator({
            "$id": (output / "expression.schema.yaml").as_uri(),
            **schemas[Path("expression.schema.yaml")],
        }, registry=schema_registry(schemas, output))

    def test_enabled_directories_mirror_paths_and_allow_cross_group_recursion(self):
        self.write("extras/nested/wrapping.yaml", {"wrap": {
            "schemaName": "wrapper", "argumentKind": "expression",
            "minArgs": 1, "maxArgs": 1,
        }})
        core = generate_schemas(load_language(self.manifest))
        self.assertNotIn(Path("extras/nested/wrapping.schema.yaml"), core)
        self.assertFalse(self.validator(core).is_valid({"plus": [1, {"wrap": [2]}]}))

        self.write("language.yaml", {"operatorDirectories": ["core", "extras"]})
        schemas = generate_schemas(load_language(self.manifest))
        self.assertEqual(set(schemas), {
            Path("expression.schema.yaml"), Path("shared.schema.yaml"),
            Path("core/math.schema.yaml"), Path("extras/nested/wrapping.schema.yaml"),
        })
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        wrapper = schemas[Path("extras/nested/wrapping.schema.yaml")]["$defs"]["wrapper"]
        self.assertEqual(
            wrapper["properties"]["wrap"]["items"]["$ref"],
            "../../expression.schema.yaml#/$defs/expression",
        )
        validator = self.validator(schemas)
        validator.validate({"plus": [1, {"wrap": [{"plus": [2, 3]}]}]})
        validator.validate({"wrap": [{"plus": [1, {"wrap": [2]}]}]})
        self.assertFalse(validator.is_valid({"wrap": [{"unknown": [1]}]}))

    def test_source_order_is_deterministic(self):
        self.write("extras/zeta.yml", {"last": {"argumentKind": "expression", "minArgs": 1}})
        self.write("core/alpha.yaml", {"first": {"argumentKind": "expression", "minArgs": 1}})
        self.write("language.yaml", {"operatorDirectories": ["extras", "core"]})
        first = load_language(self.manifest)
        self.write("language.yaml", {"operatorDirectories": ["core", "extras"]})
        second = load_language(self.manifest)
        self.assertEqual(list(first), list(second))
        self.assertEqual(list(first), sorted(first))
        self.assertEqual(generate_schemas(first), generate_schemas(second))

    def test_included_core_composes_recursive_operands(self):
        self.write("custom/wrapping.yaml", {"wrap": {
            "schemaName": "wrapper", "argumentKind": "expression",
            "minArgs": 1, "maxArgs": 1,
        }})
        self.write("language.yaml", {
            "include": ["gramson:core"], "operatorDirectories": ["custom"],
        })
        groups = load_language(self.manifest)
        self.assertEqual(len(merge_operators(groups)), 36)
        schemas = generate_schemas(groups)
        self.assertIn(Path("core/arithmetic.schema.yaml"), schemas)
        self.assertIn(Path("custom/wrapping.schema.yaml"), schemas)
        validator = self.validator(schemas)
        validator.validate({"+": [1, {"wrap": [{"var": "price"}]}]})
        validator.validate({"wrap": [{"+": [1, {"wrap": [2]}]}]})
        self.assertFalse(validator.is_valid({"wrap": [1, 2]}))
        self.assertFalse(validator.is_valid({"wrap": [{"unknown": [1]}]}))

    def test_core_only_manifest_and_bundled_sources_match_repository(self):
        expected = load_language(ROOT / "spec" / "language.yaml")
        self.assertEqual(load_core(), expected)
        for manifest in ({"include": ["gramson:core"]}, {
            "include": ["gramson:core"], "operatorDirectories": [],
        }):
            with self.subTest(manifest=manifest):
                self.write("language.yaml", manifest)
                self.assertEqual(load_language(self.manifest), expected)

    def test_core_extension_rejects_operator_and_definition_collisions(self):
        for name, schema_name, diagnostic in (
            ("+", "customAddition", "Duplicate operator"),
            ("wrap", "addition", "Duplicate schemaName"),
        ):
            with self.subTest(name=name):
                self.write("custom/wrapping.yaml", {name: {
                    "schemaName": schema_name, "argumentKind": "expression", "minArgs": 1,
                }})
                self.write("language.yaml", {
                    "include": ["gramson:core"], "operatorDirectories": ["custom"],
                })
                with self.assertRaises(ValueError) as raised:
                    load_language(self.manifest)
                self.assertIn(diagnostic, str(raised.exception))
                self.assertIn("core/arithmetic.yaml", str(raised.exception))
                self.assertIn("custom/wrapping.yaml", str(raised.exception))

    def test_local_core_directory_can_compose_with_bundled_core(self):
        self.write("core/math.yaml", {"plus": {
            "schemaName": "customPlus", "argumentKind": "expression", "minArgs": 2,
        }})
        self.write("language.yaml", {
            "include": ["gramson:core"], "operatorDirectories": ["core"],
        })
        schemas = generate_schemas(load_language(self.manifest))
        self.validator(schemas).validate({"plus": [{"+": [1, 2]}, 3]})
        self.write("language.yaml", {"operatorDirectories": ["core"]})
        operators = merge_operators(load_language(self.manifest))
        self.assertEqual(set(operators), {"plus"})
        self.assertFalse(self.validator(generate_schemas(load_language(self.manifest))).is_valid({"+": [1, 2]}))

    def test_core_include_rejects_local_output_collisions(self):
        self.write("core/arithmetic.yml", {"wrap": {
            "argumentKind": "expression", "minArgs": 1,
        }})
        self.write("language.yaml", {
            "include": ["gramson:core"], "operatorDirectories": ["core"],
        })
        with self.assertRaisesRegex(ValueError, "Output collision.*bundled core/arithmetic.yaml.*local core/arithmetic.yml"):
            load_language(self.manifest)

    def test_include_order_does_not_change_the_generated_language(self):
        self.write("language.yaml", {"include": ["gramson:core", "gramson:bitwise"]})
        first = load_language(self.manifest)
        self.write("language.yaml", {"include": ["gramson:bitwise", "gramson:core"]})
        second = load_language(self.manifest)
        self.assertEqual(list(first), list(second))
        self.assertEqual(generate_schemas(first), generate_schemas(second))

    def test_bundled_extension_can_be_selected_without_core(self):
        self.write("language.yaml", {"include": ["gramson:bitwise"]})
        groups = load_language(self.manifest)
        self.assertEqual(set(groups), {Path("extensions/bitwise.yaml")})
        schemas = generate_schemas(groups)
        validator = self.validator(schemas)
        validator.validate({"&": [1, {"~": [2]}]})
        self.assertFalse(validator.is_valid({"+": [1, 2]}))

    def test_bundled_extension_composes_with_core_and_local_groups(self):
        self.write("custom/wrap.yaml", {"wrap": {
            "schemaName": "wrapper", "argumentKind": "expression", "minArgs": 1,
        }})
        self.write("language.yaml", {
            "include": ["gramson:core", "gramson:bitwise"],
            "operatorDirectories": ["custom"],
        })
        schemas = generate_schemas(load_language(self.manifest))
        self.assertIn(Path("extensions/bitwise.schema.yaml"), schemas)
        self.validator(schemas).validate({"+": [{"wrap": [{"&": [{"var": "mask"}, 3]}]}, 1]})

    def test_bundled_extension_rejects_local_output_collisions(self):
        self.write("extensions/bitwise.yml", {"wrap": {
            "argumentKind": "expression", "minArgs": 1,
        }})
        self.write("language.yaml", {
            "include": ["gramson:bitwise"], "operatorDirectories": ["extensions"],
        })
        with self.assertRaisesRegex(ValueError, "Output collision.*bundled extensions/bitwise.yaml.*local extensions/bitwise.yml"):
            load_language(self.manifest)

    def test_bundled_extension_rejects_operator_and_definition_collisions(self):
        for name, schema_name, diagnostic in (
            ("&", "anotherBitwiseAnd", "Duplicate operator"),
            ("wrap", "bitwiseAnd", "Duplicate schemaName"),
        ):
            with self.subTest(name=name):
                self.write("custom/duplicate.yaml", {name: {
                    "schemaName": schema_name, "argumentKind": "expression", "minArgs": 1,
                }})
                self.write("language.yaml", {
                    "include": ["gramson:bitwise"], "operatorDirectories": ["custom"],
                })
                with self.assertRaises(ValueError) as raised:
                    load_language(self.manifest)
                self.assertIn(diagnostic, str(raised.exception))
                self.assertIn("extensions/bitwise.yaml", str(raised.exception))
                self.assertIn("custom/duplicate.yaml", str(raised.exception))

    def test_duplicate_operator_reports_both_sources(self):
        self.write("core/other.yaml", {"plus": {
            "schemaName": "otherAddition", "argumentKind": "expression", "minArgs": 1,
        }})
        with self.assertRaisesRegex(ValueError, "Duplicate operator.*core/math.yaml.*core/other.yaml"):
            load_language(self.manifest)

    def test_duplicate_schema_name_reports_both_sources(self):
        self.write("core/other.yaml", {"other": {
            "schemaName": "addition", "argumentKind": "expression", "minArgs": 1,
        }})
        with self.assertRaisesRegex(ValueError, "Duplicate schemaName.*core/math.yaml.*core/other.yaml"):
            load_language(self.manifest)

    def test_duplicate_keys_inside_yaml_are_rejected(self):
        path = self.directory / "core" / "math.yaml"
        path.write_text("plus: {}\nplus: {}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "math.yaml:2: duplicate YAML key 'plus'"):
            load_language(self.manifest)

    def test_output_basename_collisions_are_rejected(self):
        self.write("core/math.yml", {"other": {"argumentKind": "expression", "minArgs": 1}})
        with self.assertRaisesRegex(ValueError, "Output collision.*math.yaml.*math.yml"):
            load_language(self.manifest)

    def test_invalid_manifests_are_rejected(self):
        manifests = [
            None, [], {}, {"operatorDirectories": []}, {"operatorDirectories": "core"},
            {"operatorDirectories": [None]}, {"operatorDirectories": [""]},
            {"operatorDirectories": ["missing"]}, {"operatorDirectories": [".."]},
            {"operatorDirectories": ["."]}, {"operatorDirectories": [str(self.directory)]},
            {"operatorDirectories": ["core", "core"]},
            {"operatorDirectories": ["core"], "typo": True},
            {"include": ["gramson:core"], "operatorDirectories": None},
            {"include": ["gramson:core"], "typo": True},
            {"include": "gramson:core"}, {"include": None},
            {"include": []}, {"include": [None]},
            {"include": [["gramson:bitwise"]]},
            {"include": ["gramson:unknown"]}, {"include": ["../../bitwise"]},
            {"include": ["gramson:core", "gramson:core"]},
            {"include": ["gramson:bitwise", "gramson:bitwise"]},
            {"extends": "gramson:core"}, {"extensions": ["gramson:bitwise"]},
            {"include": ["gramson:core"], "extends": "gramson:core"},
        ]
        for manifest in manifests:
            with self.subTest(manifest=manifest):
                self.write("language.yaml", manifest)
                with self.assertRaises(ValueError):
                    load_language(self.manifest)

    def test_empty_groups_and_malformed_definitions_name_the_source(self):
        for definition in ({}, [], {"bad": {"argumentKind": "number", "minArgs": 1}}):
            with self.subTest(definition=definition):
                self.write("core/math.yaml", definition)
                with self.assertRaisesRegex(ValueError, "core/math.yaml"):
                    load_language(self.manifest)

    def test_empty_directory_is_rejected(self):
        (self.directory / "empty").mkdir()
        self.write("language.yaml", {"operatorDirectories": ["empty"]})
        with self.assertRaisesRegex(ValueError, "no YAML operator files"):
            load_language(self.manifest)

    def test_paths_and_definition_names_are_escaped_in_references(self):
        self.write("extra space/group #1.yaml", {"custom": {
            "schemaName": "name/a~b #é", "argumentKind": "expression", "minArgs": 1,
        }})
        self.write("language.yaml", {"operatorDirectories": ["core", "extra space"]})
        schemas = generate_schemas(load_language(self.manifest))
        self.validator(schemas).validate({"custom": [{"plus": [1, 2]}]})
        references = schemas[Path("expression.schema.yaml")]["$defs"]["expression"]["oneOf"]
        self.assertIn({
            "$ref": "extra%20space/group%20%231.schema.yaml#/$defs/name~1a~0b%20%23%C3%A9"
        }, references)

    def test_invalid_source_does_not_overwrite_existing_output(self):
        output = self.directory / "output"
        output.mkdir()
        existing = output / "expression.schema.yaml"
        existing.write_text("unchanged", encoding="utf-8")
        self.write("core/other.yaml", {"plus": {
            "schemaName": "other", "argumentKind": "expression", "minArgs": 1,
        }})
        result = subprocess.run([
            sys.executable, str(ROOT / "tools" / "generate_schema.py"),
            "--manifest", str(self.manifest), "--output-directory", str(output),
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate operator", result.stderr)
        self.assertEqual(existing.read_text(encoding="utf-8"), "unchanged")


if __name__ == "__main__":
    unittest.main()
