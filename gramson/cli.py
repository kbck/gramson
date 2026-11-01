import argparse
import json
import math
import sys
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import url2pathname

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, best_match
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from .generation import (
    generate_schemas,
    load_core,
    load_language,
    read_yaml,
    write_schemas,
)

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


def expression_validator(schema_path=None):
    """Load bundled or generated local schemas with no remote retrieval."""
    schemas = {}

    def load_schema(source):
        if source.name.endswith(".json"):
            schema = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        else:
            schema = read_yaml(source)
        Draft202012Validator.check_schema(schema)
        return schema

    if schema_path is not None:
        schema_path = Path(schema_path).resolve()
        root = schema_path.parent

        @lru_cache(maxsize=None)
        def retrieve_local(uri):
            parsed = urlsplit(uri)
            if parsed.scheme != "file" or parsed.netloc:
                raise NoSuchResource(ref=uri)
            source = Path(url2pathname(parsed.path)).resolve()
            if not source.is_relative_to(root):
                raise NoSuchResource(ref=uri)
            return Resource.from_contents(load_schema(source), default_specification=DRAFT202012)

        # Resolve only referenced files, without scanning unrelated directories
        # or falling back to package resources or network retrieval.
        registry = Registry(retrieve=retrieve_local).with_resource(
            schema_path.as_uri(),
            Resource.from_contents(load_schema(schema_path), default_specification=DRAFT202012),
        )
        return Draft202012Validator({"$ref": schema_path.as_uri()}, registry=registry)

    def read_directory(directory, prefix=""):
        for item in directory.iterdir():
            relative = prefix + item.name
            if item.is_dir():
                read_directory(item, relative + "/")
            elif item.name.endswith((".schema.yaml", ".schema.yml", ".schema.json")):
                schemas[relative] = load_schema(item)

    read_directory(files("gramson.schemas"))
    registry = Registry().with_resources(
        (SCHEMA_BASE + quote(name, safe="/"), Resource.from_contents(schema, default_specification=DRAFT202012))
        for name, schema in schemas.items()
    )
    return Draft202012Validator({
        "$ref": SCHEMA_BASE + "expression.schema.yaml",
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
    parser = argparse.ArgumentParser(prog="gramson", description="Generate grammars and validate Gramson expression syntax offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Generate a self-contained expression grammar.")
    generate.add_argument("--manifest", type=Path, help="Language manifest; defaults to the bundled core language.")
    generate.add_argument("--spec-path", type=Path, action="append", default=[], help="Search root for external namespace:group includes (repeatable).")
    generate.add_argument("--output-directory", type=Path, default=Path("schema"), help="Output directory (default: schema).")
    validate = commands.add_parser("validate", help="Validate one JSON or YAML expression.")
    validate.add_argument("expression", help="Expression file, or - to read stdin.")
    validate.add_argument("--format", choices=("json", "yaml"), help="Override file format; stdin defaults to JSON.")
    validate.add_argument("--schema", type=Path, help="Generated schema entry point; defaults to the bundled grammar.")
    options = parser.parse_args(argv)
    if options.command == "generate":
        try:
            if options.spec_path and options.manifest is None:
                raise ValueError("--spec-path requires --manifest.")
            groups = load_core() if options.manifest is None else load_language(options.manifest, spec_paths=options.spec_path)
            schemas = generate_schemas(groups)
            write_schemas(schemas, options.output_directory)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError) as error:
            print(f"gramson generate: {error}", file=sys.stderr)
            return 2
        print(f"Generated {len(schemas)} schemas in {options.output_directory}")
        return 0
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

    try:
        error = next(expression_validator(options.schema).iter_errors(expression), None)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError, SchemaError, Unresolvable, RecursionError) as error:
        print(f"{label}: schema error: {error}", file=sys.stderr)
        return 2
    if error is not None:
        location, message = error_detail(error)
        print(f"{label}: invalid expression at {location}: {message}", file=sys.stderr)
        return 1
    print(f"{label}: valid expression")
    return 0
