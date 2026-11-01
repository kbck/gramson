from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from gramson.cli import main


class CLITests(unittest.TestCase):
    def invoke(self, source, *arguments):
        stdout, stderr = StringIO(), StringIO()
        with patch("sys.stdin", StringIO(source)), redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["validate", "-", *arguments])
        return status, stdout.getvalue(), stderr.getvalue()

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
