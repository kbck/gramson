import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from jsonschema import Draft202012Validator

from gramson.generation import (
    generate_schemas,
    load_core,
    load_language,
    merge_operators,
)
from schema_support import schema_registry

WRAP = {"wrap": {
    "schemaName": "wrapper", "argumentKind": "expression", "minArgs": 1, "maxArgs": 1,
}}


class ExternalIncludeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.library = self.directory / "vendor"
        self.manifest = self.directory / "language.yaml"
        self.write("vendor/mystuff/myops/ops.yaml", WRAP)
        self.write("language.yaml", {"include": ["gramson:core", "mystuff:myops"]})

    def write(self, relative, value):
        path = self.directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, sort_keys=False))

    def load(self, paths=None):
        return load_language(self.manifest, spec_paths=paths if paths is not None else [self.library])

    def validator(self, groups):
        schemas = generate_schemas(groups)
        output = self.directory / "output"
        return Draft202012Validator({
            "$id": (output / "expression.schema.yaml").as_uri(),
            **schemas[Path("expression.schema.yaml")],
        }, registry=schema_registry(schemas, output))

    def test_external_namespace_composes_with_core_and_preserves_relative_layout(self):
        groups = self.load()
        self.assertIn(Path("mystuff/myops/ops.yaml"), groups)
        self.assertIn(Path("mystuff/myops/ops.schema.yaml"), generate_schemas(groups))
        validator = self.validator(groups)
        validator.validate({"+": [1, {"wrap": [{"+": [2, {"var": "price"}]}]}]})
        self.assertFalse(validator.is_valid({"mystuff:wrap": [1]}))

    def test_external_namespace_does_not_implicitly_include_core(self):
        self.write("language.yaml", {"include": ["mystuff:myops"]})
        groups = self.load()
        self.assertEqual(set(merge_operators(groups)), {"wrap"})
        self.validator(groups).validate({"wrap": [1]})
        self.assertFalse(self.validator(groups).is_valid({"+": [1, 2]}))

    def test_repeated_search_roots_and_root_order_do_not_change_output(self):
        other = self.directory / "other"
        other.mkdir()
        first = self.load([self.library, other])
        second = self.load([other, self.library, self.library])
        self.assertEqual(list(first), list(second))
        self.assertEqual(generate_schemas(first), generate_schemas(second))

    def test_namespaces_can_come_from_different_search_roots(self):
        self.write("other/other/more/ops.yaml", {"otherWrap": {
            "schemaName": "otherWrapper", "argumentKind": "expression", "minArgs": 1,
        }})
        self.write("language.yaml", {"include": ["gramson:core", "mystuff:myops", "other:more"]})
        groups = self.load([self.directory / "other", self.library])
        self.validator(groups).validate({"wrap": [{"otherWrap": [{"var": "value"}]}]})

    def test_ambiguous_include_reports_both_locations(self):
        self.write("other/mystuff/myops/ops.yaml", WRAP)
        with self.assertRaises(ValueError) as raised:
            self.load([self.library, self.directory / "other"])
        diagnostic = str(raised.exception)
        self.assertIn("Ambiguous include 'mystuff:myops'", diagnostic)
        self.assertIn(str(self.library / "mystuff/myops"), diagnostic)
        self.assertIn(str(self.directory / "other/mystuff/myops"), diagnostic)

    def test_unknown_names_and_invalid_search_paths_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "provide --spec-path"):
            self.load([])
        for path in (self.directory / "missing", self.manifest):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "existing directory"):
                self.load([path])
        self.write("language.yaml", {"include": ["mystuff:missing"]})
        with self.assertRaisesRegex(ValueError, "Unknown include.*searched"):
            self.load()

    def test_gramson_namespace_cannot_be_shadowed_or_extended_externally(self):
        self.write("vendor/gramson/core/ops.yaml", WRAP)
        self.write("vendor/gramson/unknown/ops.yaml", WRAP)
        self.write("language.yaml", {"include": ["gramson:core"]})
        self.assertEqual(self.load(), load_core())
        self.write("language.yaml", {"include": ["gramson:unknown"]})
        with self.assertRaisesRegex(ValueError, "gramson: is reserved"):
            self.load()

    def test_invalid_or_repeated_external_identifiers_are_rejected(self):
        for name in ("mystuff", "MyStuff:ops", "mystuff:../ops", "mystuff:some/ops", "mystuff:a:b"):
            with self.subTest(name=name):
                self.write("language.yaml", {"include": [name]})
                with self.assertRaisesRegex(ValueError, "invalid include"):
                    self.load()
        self.write("language.yaml", {"include": ["mystuff:myops", "mystuff:myops"]})
        with self.assertRaisesRegex(ValueError, "repeated include"):
            self.load()

    def test_external_and_core_operator_or_definition_names_must_be_unique(self):
        for name, schema_name, diagnostic in (
            ("+", "anotherAddition", "Duplicate operator"),
            ("wrap", "addition", "Duplicate schemaName"),
        ):
            with self.subTest(name=name):
                self.write("vendor/mystuff/myops/ops.yaml", {name: {
                    "schemaName": schema_name, "argumentKind": "expression", "minArgs": 1,
                }})
                with self.assertRaises(ValueError) as raised:
                    self.load()
                self.assertIn(diagnostic, str(raised.exception))
                self.assertIn("core/arithmetic.yaml", str(raised.exception))
                self.assertIn("mystuff/myops/ops.yaml", str(raised.exception))

    def test_external_and_local_output_paths_must_be_unique(self):
        self.write("mystuff/myops/ops.yaml", {"other": {"argumentKind": "expression", "minArgs": 1}})
        self.write("language.yaml", {
            "include": ["mystuff:myops"], "operatorDirectories": ["mystuff"],
        })
        with self.assertRaisesRegex(ValueError, "Output collision.*include 'mystuff:myops'.*local"):
            self.load()

    def test_output_collisions_inside_an_external_group_are_rejected(self):
        self.write("vendor/mystuff/myops/ops.yml", {"other": {"argumentKind": "expression", "minArgs": 1}})
        with self.assertRaisesRegex(ValueError, "Output collision.*ops.yaml.*ops.yml"):
            self.load()

    def test_empty_external_groups_are_rejected(self):
        (self.library / "mystuff/empty").mkdir()
        self.write("language.yaml", {"include": ["mystuff:empty"]})
        with self.assertRaisesRegex(ValueError, "no YAML operator files"):
            self.load()

    def test_group_and_operator_symlinks_cannot_escape_the_selected_tree(self):
        (self.directory / "outside").mkdir()
        (self.library / "mystuff/linked").symlink_to(self.directory / "outside", target_is_directory=True)
        self.write("language.yaml", {"include": ["mystuff:linked"]})
        with self.assertRaisesRegex(ValueError, "escapes its spec search path"):
            self.load()
        self.write("outside/ops.yaml", WRAP)
        (self.library / "mystuff/myops/link.yaml").symlink_to(self.directory / "outside/ops.yaml")
        self.write("language.yaml", {"include": ["mystuff:myops"]})
        with self.assertRaisesRegex(ValueError, "must stay inside include"):
            self.load()


if __name__ == "__main__":
    unittest.main()
