import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from jsonschema import Draft202012Validator

from gramson.generation import generate_schema, load_language, read_yaml

ROOT = Path(__file__).resolve().parents[1]


class AuthoringSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = {}
        for name in ("operator-spec", "language-manifest"):
            schema = read_yaml(ROOT / "spec" / "schemas" / f"{name}.schema.yaml")
            Draft202012Validator.check_schema(schema)
            cls.validators[name] = Draft202012Validator(schema)

    def test_repository_and_example_sources_validate(self):
        manifests = [ROOT / "spec/language.yaml"]
        manifests.extend(sorted((ROOT / "examples").rglob("language.yaml")))
        manifests.append(ROOT / "examples/extension/standalone.yaml")
        for path in manifests:
            with self.subTest(manifest=path):
                self.validators["language-manifest"].validate(read_yaml(path))
                groups = load_language(
                    path, spec_paths=[ROOT / "examples/external/vendor"]
                )
                for definitions in groups.values():
                    self.validators["operator-spec"].validate(definitions)

    def test_manifest_selection_forms(self):
        for manifest in (
            {"include": ["mystuff:myops"]},
            {"include": [], "operatorDirectories": ["custom"]},
            {"include": ["gramson:core"], "operatorDirectories": []},
        ):
            with self.subTest(manifest=manifest):
                self.validators["language-manifest"].validate(manifest)

    def test_malformed_manifests_are_rejected(self):
        for manifest in (
            None, {}, {"include": []}, {"operatorDirectories": []},
            {"include": "gramson:core"}, {"include": ["invalid"]},
            {"include": ["mystuff:myops\n"]},
            {"include": ["gramson:core", "gramson:core"]},
            {"operatorDirectories": [" "]},
            {"operatorDirectories": ["custom", "custom"]},
            {"include": ["gramson:core"], "removeOperators": ["log"]},
        ):
            with self.subTest(manifest=manifest):
                self.assertFalse(self.validators["language-manifest"].is_valid(manifest))

    def test_malformed_operator_definitions_are_rejected(self):
        base = {"argumentKind": "expression", "minArgs": 1}
        for definition in (
            {}, {"minArgs": 1}, {"argumentKind": "expression"},
            {**base, "unknown": True}, {**base, "argumentKind": "number"},
            {**base, "minArgs": -1}, {**base, "minArgs": True},
            {**base, "maxArgs": None}, {**base, "shorthand": 1},
            {**base, "schemaName": "expression"}, {**base, "schemaName": ""},
            {**base, "summary": " \n"},
            {**base, "minArgs": 2, "shorthand": True},
            {**base, "minArgs": 0, "maxArgs": 0, "shorthand": True},
        ):
            with self.subTest(definition=definition):
                self.assertFalse(self.validators["operator-spec"].is_valid({"op": definition}))
        for operators in ({}, {"": base}, {"op": None}):
            with self.subTest(operators=operators):
                self.assertFalse(self.validators["operator-spec"].is_valid(operators))

    def test_manifest_schema_errors_precede_source_resolution(self):
        with TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "language.yaml"
            manifest.write_text("include: [INVALID]\noperatorDirectories: [missing]\n")
            with self.assertRaises(ValueError) as raised:
                load_language(manifest)
            self.assertIn(f"{manifest}#/include/0:", str(raised.exception))
            self.assertIn("does not match", str(raised.exception))

    def test_local_and_external_operator_errors_identify_source_and_field(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "language.yaml"
            for selection, relative in (
                ({"operatorDirectories": ["custom"]}, "custom/ops.yaml"),
                ({"include": ["mystuff:myops"]}, "vendor/mystuff/myops/ops.yaml"),
            ):
                with self.subTest(selection=selection):
                    source = root / relative
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_text("wrap:\n  argumentKind: expression\n  minArgs: false\n")
                    manifest.write_text(yaml.safe_dump(selection))
                    with self.assertRaises(ValueError) as raised:
                        load_language(manifest, spec_paths=[root / "vendor"] if "include" in selection else [])
                    self.assertIn(f"{source}#/wrap/minArgs:", str(raised.exception))
                    self.assertIn("not of type 'integer'", str(raised.exception))

    def test_python_generation_validates_schema_and_retains_arity_checks(self):
        with self.assertRaisesRegex(ValueError, "operator specification#/wrap/argumentKind:"):
            generate_schema({"wrap": {"argumentKind": "invalid", "minArgs": 1}})
        for definition in (
            {"minArgs": 2, "maxArgs": 1},
            {"minArgs": 1.0}, {"minArgs": 1, "maxArgs": 2.0},
        ):
            with self.subTest(definition=definition), self.assertRaises(ValueError):
                generate_schema({"wrap": {"argumentKind": "expression", **definition}})
