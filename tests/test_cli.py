from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from gramson.cli import main
from schema_support import read_schemas


class CLITests(unittest.TestCase):
    def invoke(self, source, *arguments):
        return self.invoke_command(["validate", "-", *arguments], source)

    def invoke_command(self, arguments, source=""):
        stdout, stderr = StringIO(), StringIO()
        with patch("sys.stdin", StringIO(source)), redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(arguments)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_generate_defaults_to_bundled_core(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "schema"
            status, _, stderr = self.invoke_command(["generate", "--output-directory", str(output)])
            self.assertEqual(status, 0, stderr)
            root = Path(__file__).resolve().parents[1]
            self.assertEqual(read_schemas(output), read_schemas(root / "schema"))

    def test_ready_to_run_extension_examples(self):
        root = Path(__file__).resolve().parents[1]
        example = root / "examples" / "extension"
        for manifest, expected_nested in (("language.yaml", 0), ("standalone.yaml", 1)):
            with self.subTest(manifest=manifest), TemporaryDirectory() as temporary:
                output = Path(temporary) / "schema"
                status, _, stderr = self.invoke_command([
                    "generate", "--manifest", str(example / manifest),
                    "--output-directory", str(output),
                ])
                self.assertEqual(status, 0, stderr)
                for filename, expected in (
                    ("nested.yaml", expected_nested), ("nested.json", expected_nested),
                    ("wrap-only.yaml", 0), ("invalid-arity.yaml", 1),
                ):
                    with self.subTest(expression=filename):
                        status, _, stderr = self.invoke_command([
                            "validate", str(example / "expressions" / filename),
                            "--schema", str(output / "expression.schema.yaml"),
                        ])
                        self.assertEqual(status, expected, stderr)

    def test_custom_language_output_is_portable_and_self_contained(self):
        for include_core in (False, True):
            with self.subTest(include_core=include_core), TemporaryDirectory() as portable:
                relocated = Path(portable) / "language #1"
                with TemporaryDirectory() as temporary:
                    source = Path(temporary)
                    (source / "custom").mkdir()
                    (source / "custom/wrap.yaml").write_text(
                        "wrap:\n  schemaName: wrapper\n  argumentKind: expression\n  minArgs: 1\n  maxArgs: 1\n"
                    )
                    manifest = source / "language.yaml"
                    manifest.write_text(
                        ("include: [gramson:core]\n" if include_core else "")
                        + "operatorDirectories: [custom]\n"
                    )
                    output = source / "generated"
                    status, _, stderr = self.invoke_command([
                        "generate", "--manifest", str(manifest), "--output-directory", str(output),
                    ])
                    self.assertEqual(status, 0, stderr)
                    shutil.copytree(output, relocated)
                # The original source and output are gone. Local validation must
                # also work without consulting any installed package resources.
                schema = str(relocated / "expression.schema.yaml")
                with patch("gramson.cli.files", side_effect=AssertionError("Unexpected bundled resource lookup")):
                    for expression, expected in (
                        ({"wrap": [1]}, 0),
                        ({"wrap": [1, 2]}, 1),
                        ({"wrap": [{"+": [1, {"wrap": [2]}]}]}, 0 if include_core else 1),
                        ({"+": [{"wrap": [1]}, 2]}, 0 if include_core else 1),
                    ):
                        with self.subTest(expression=expression):
                            status, _, stderr = self.invoke(json.dumps(expression), "--schema", schema)
                            self.assertEqual(status, expected, stderr)
                self.assertEqual(self.invoke('{"wrap":[1]}')[0], 1)

    def test_invalid_generation_preserves_existing_output(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "custom").mkdir()
            (directory / "custom/duplicate.yaml").write_text(
                "'+':\n  schemaName: anotherAddition\n  argumentKind: expression\n  minArgs: 1\n"
            )
            manifest = directory / "language.yaml"
            manifest.write_text("include: [gramson:core]\noperatorDirectories: [custom]\n")
            output = directory / "output"
            output.mkdir()
            sentinel = output / "expression.schema.yaml"
            sentinel.write_text("unchanged")
            status, stdout, stderr = self.invoke_command([
                "generate", "--manifest", str(manifest), "--output-directory", str(output),
            ])
            self.assertEqual(status, 2)
            self.assertEqual(stdout, "")
            self.assertIn("Duplicate operator", stderr)
            self.assertEqual(sentinel.read_text(), "unchanged")
            self.assertEqual(list(output.iterdir()), [sentinel])

    def test_schema_errors_are_reported_without_remote_retrieval(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "schema.json"
            for contents in (None, "{", '{"type":"unknown"}', '{"$ref":"https://example.invalid/missing"}'):
                with self.subTest(contents=contents):
                    if contents is not None:
                        path.write_text(contents)
                    status, stdout, stderr = self.invoke("1", "--schema", str(path))
                    self.assertEqual(status, 2)
                    self.assertEqual(stdout, "")
                    self.assertIn("schema error", stderr)
            path.write_text('{"type":"integer"}')
            self.assertEqual(self.invoke("1", "--schema", str(path))[0], 0)
            self.assertEqual(self.invoke('"text"', "--schema", str(path))[0], 1)

    def test_custom_schema_loads_only_referenced_files_within_its_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "schema"
            directory.mkdir()
            entry = directory / "entry.json"
            entry.write_text('{"$ref":"value.yaml"}')
            (directory / "value.yaml").write_text("type: integer\n")
            (directory / "unused.schema.yaml").write_text("not: valid: yaml")
            self.assertEqual(self.invoke("1", "--schema", str(entry))[0], 0)
            self.assertEqual(self.invoke('"text"', "--schema", str(entry))[0], 1)
            (root / "outside.json").write_text('{"type":"integer"}')
            entry.write_text('{"$ref":"../outside.json"}')
            status, _, stderr = self.invoke("1", "--schema", str(entry))
            self.assertEqual(status, 2)
            self.assertIn("schema error", stderr)

    def test_json_and_yaml_files_from_another_directory(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            expressions = {
                "expression.json": json.dumps({"+": [{"var": "price"}, 1]}),
                "expression.yaml": "'+':\n  - var: price\n  - 1\n",
                "expression.yml": "if: [false, 1, 2]\n",
            }
            for filename, source in expressions.items():
                with self.subTest(filename=filename):
                    (directory / filename).write_text(source)
                    result = subprocess.run(
                        [str(Path(sys.executable).with_name("gramson")), "validate", filename],
                        cwd=directory, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("valid expression", result.stdout)
                    self.assertEqual(result.stderr, "")

    def test_stdin_and_scalar_expressions(self):
        for source in ('null', 'false', '42', '"text"', '[1, {"var":"x"}]'):
            with self.subTest(source=source):
                status, stdout, stderr = self.invoke(source)
                self.assertEqual(status, 0, stderr)
                self.assertEqual(stdout, "stdin: valid expression\n")
                self.assertEqual(stderr, "")
        self.assertEqual(self.invoke("'?:': [true, 1, 0]", "--format", "yaml")[0], 0)

    def test_invalid_expressions_have_relevant_locations(self):
        for expression, detail in (
            ({"+": []}, "should be non-empty"),
            ({"unknown": []}, "Unknown operator"),
            ({"+": [1, {"unknown": []}]}, "Unknown operator"),
            ({}, "exactly one registered operator"),
            ({"var": "x", "extra": 1}, "exactly one registered operator"),
        ):
            with self.subTest(expression=expression):
                status, stdout, stderr = self.invoke(json.dumps(expression))
                self.assertEqual(status, 1)
                self.assertEqual(stdout, "")
                self.assertIn("invalid expression at $", stderr)
                self.assertIn(detail, stderr)
                if expression == {"+": [1, {"unknown": []}]}:
                    self.assertIn("[1]", stderr)

    def test_malformed_inputs_and_non_json_yaml_values(self):
        cases = [
            ("", ()),
            ("{", ()),
            ('{"var":"x","var":"y"}', ()),
            ("NaN", ()),
            ("1e9999", ()),
            ("var: [", ("--format", "yaml")),
            ("var: x\nvar: y", ("--format", "yaml")),
            ("1: value", ("--format", "yaml")),
            ("2026-11-01", ("--format", "yaml")),
            (".inf", ("--format", "yaml")),
            ("!!python/object:example {}", ("--format", "yaml")),
            ("&loop [*loop]", ("--format", "yaml")),
            ("---\n1\n---\n2", ("--format", "yaml")),
        ]
        for source, arguments in cases:
            with self.subTest(source=source):
                status, stdout, stderr = self.invoke(source, *arguments)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("input error", stderr)

    def test_repeated_noncyclic_yaml_aliases(self):
        status, _, stderr = self.invoke("[&value [1, 2], *value]", "--format", "yaml")
        self.assertEqual(status, 0, stderr)

    def test_missing_file(self):
        with TemporaryDirectory() as temporary:
            stderr = StringIO()
            with redirect_stderr(stderr):
                status = main(["validate", str(Path(temporary) / "missing.json")])
            self.assertEqual(status, 2)
            self.assertIn("input error", stderr.getvalue())

    def test_module_entry_point(self):
        result = subprocess.run(
            [sys.executable, "-m", "gramson", "validate", "-"],
            input='{"if":[]}', capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid expression", result.stdout)


if __name__ == "__main__":
    unittest.main()
