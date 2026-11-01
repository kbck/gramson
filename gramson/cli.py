import argparse
from importlib.resources import files
import json
import math
from pathlib import Path
import sys
from urllib.parse import quote

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry, Resource
import yaml


SCHEMA_BASE = "https://gramson.invalid/schema/"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str):
            raise ValueError("Object keys must be strings.")
        if key in result:
            raise ValueError(f"Duplicate object key: {key!r}.")
        result[key] = value
    return result


class ExpressionLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        return unique_object(self.construct_pairs(node, deep=deep))


def check_json_value(value, ancestors=None):
    """Reject YAML values that cannot be represented as finite JSON data."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Numbers must be finite JSON numbers.")
        return
    if not isinstance(value, (list, dict)):
        raise ValueError(f"Unsupported JSON value type: {type(value).__name__}.")
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ValueError("Cyclic YAML aliases cannot represent JSON values.")
    ancestors.add(id(value))
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Object keys must be strings.")
        children = value.values()
    else:
        children = value
    for child in children:
        check_json_value(child, ancestors)
    ancestors.remove(id(value))


def expression_validator():
    """Load bundled schemas into a registry with no remote retrieval."""
    schemas = {}

    def read_directory(directory, prefix=""):
        for item in directory.iterdir():
            relative = prefix + item.name
            if item.is_dir():
                read_directory(item, relative + "/")
            elif item.name.endswith(".schema.yaml"):
                schemas[relative] = yaml.safe_load(item.read_text(encoding="utf-8"))

    read_directory(files("gramson.schemas"))
    registry = Registry().with_resources(
        (SCHEMA_BASE + quote(name, safe="/"), Resource.from_contents(schema))
        for name, schema in schemas.items()
    )
    return Draft202012Validator({
        "$id": SCHEMA_BASE + "expression.schema.yaml",
        **schemas["expression.schema.yaml"],
    }, registry=registry)


def error_detail(error):
    """Select the matching operator's failure from recursive oneOf branches."""
    while error.context:
        candidates = list(error.context)
        if isinstance(error.instance, dict):
            if len(error.instance) != 1:
                return error.json_path, "Expected exactly one registered operator key."
            operator = next(iter(error.instance))
            matching = [child for child in candidates if child.path and child.path[0] == operator]
            if not matching:
                return error.json_path, f"Unknown operator {operator!r}."
            candidates = matching
        elif isinstance(error.instance, list):
            relevant = [child for child in candidates if child.validator not in ("type", "not")]
            if relevant:
                candidates = relevant
        error = best_match(candidates)
    return error.json_path, error.message


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gramson", description="Validate Gramson expression syntax offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate one JSON or YAML expression.")
    validate.add_argument("expression", help="Expression file, or - to read stdin.")
    validate.add_argument("--format", choices=("json", "yaml"), help="Override file format; stdin defaults to JSON.")
    options = parser.parse_args(argv)
    label = "stdin" if options.expression == "-" else options.expression
    input_format = options.format or (
        "yaml" if Path(options.expression).suffix.lower() in (".yaml", ".yml") else "json"
    )
    try:
        source = sys.stdin.read() if options.expression == "-" else Path(options.expression).read_text(encoding="utf-8")
        if not source.strip():
            raise ValueError("Expected one expression; input is empty.")
        expression = (
            yaml.load(source, Loader=ExpressionLoader)
            if input_format == "yaml"
            else json.loads(source, object_pairs_hook=unique_object)
        )
        check_json_value(expression)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError) as error:
        print(f"{label}: input error: {error}", file=sys.stderr)
        return 2

    error = next(expression_validator().iter_errors(expression), None)
    if error is not None:
        location, message = error_detail(error)
        print(f"{label}: invalid expression at {location}: {message}", file=sys.stderr)
        return 1
    print(f"{label}: valid expression")
    return 0
