from importlib.resources import files
import posixpath
from pathlib import Path
from urllib.parse import quote

import yaml


BUNDLED_INCLUDES = {
    "gramson:core": Path("core"),
    "gramson:bitwise": Path("extensions/bitwise.yaml"),
}


def generate_schema(operators):
    if not isinstance(operators, dict) or not operators:
        raise ValueError("The registry must be a nonempty object.")

    alternatives = [
        {"$ref": "#/$defs/scalarLiteral"},
        {"$ref": "#/$defs/arrayExpression"},
    ]
    definitions = {
        "expression": {"oneOf": alternatives},
        "scalarLiteral": {"type": ["null", "boolean", "number", "string"]},
        "arrayExpression": {
            "type": "array", "items": {"$ref": "#/$defs/expression"}
        },
    }
    for name, definition in operators.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Operator names must be nonempty strings.")
        if not isinstance(definition, dict):
            raise ValueError(f"{name}: the definition must be an object.")
        allowed = {
            "argumentKind", "minArgs", "maxArgs", "shorthand", "schemaName",
            "title", "summary", "description",
        }
        if definition.keys() - allowed:
            raise ValueError(f"{name}: unsupported definition fields.")
        for field in ("title", "summary", "description"):
            if field in definition and (
                not isinstance(definition[field], str) or not definition[field].strip()
            ):
                raise ValueError(f"{name}: {field} must be a nonempty string.")

        schema_name = definition.get("schemaName", f"operator_{name}")
        if not isinstance(schema_name, str) or not schema_name:
            raise ValueError(f"{name}: schemaName must be a nonempty string.")
        if schema_name in definitions:
            raise ValueError(f"{name}: duplicate or reserved schemaName {schema_name!r}.")

        kind = definition.get("argumentKind")
        minimum = definition.get("minArgs")
        maximum = definition.get("maxArgs")
        shorthand = definition.get("shorthand", False)
        if kind not in ("string", "expression"):
            raise ValueError(f"{name}: argumentKind must be string or expression.")
        if type(minimum) is not int or minimum < 0:
            raise ValueError(f"{name}: minArgs must be a nonnegative integer.")
        if "maxArgs" in definition and (
            type(maximum) is not int or maximum < minimum
        ):
            raise ValueError(f"{name}: maxArgs must be an integer >= minArgs.")
        if type(shorthand) is not bool:
            raise ValueError(f"{name}: shorthand must be a boolean.")
        if shorthand and (minimum > 1 or maximum == 0):
            raise ValueError(f"{name}: shorthand requires an allowed arity of one.")

        argument = (
            {"type": "string"}
            if kind == "string"
            else {"$ref": "#/$defs/expression"}
        )
        arguments = {"type": "array", "items": argument, "minItems": minimum}
        if maximum is not None:
            arguments["maxItems"] = maximum
        unwrapped = {**argument, "not": {"type": "array"}}
        value = {"oneOf": [unwrapped, arguments]} if shorthand else arguments
        definitions[schema_name] = {
            "title": definition.get("title", f"{name} expression"),
            "type": "object",
            "required": [name],
            "additionalProperties": False,
            "properties": {name: value},
        }
        documentation = [
            definition[field] for field in ("summary", "description")
            if field in definition
        ]
        if documentation:
            definitions[schema_name]["description"] = "\n\n".join(documentation)
        pointer_token = schema_name.replace("~", "~0").replace("/", "~1")
        alternatives.append({"$ref": f"#/$defs/{quote(pointer_token, safe='')}"})

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Gramson expression grammar",
        "description": "Generated structural grammar; no evaluation or semantic typing.",
        "$ref": "#/$defs/expression",
        "$defs": definitions,
    }

class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(
                    f"{self.name}:{key_node.start_mark.line + 1}: duplicate YAML key {key!r}"
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def read_yaml(path):
    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=UniqueKeyLoader)


def _load_bundled(name):
    """Load installed declarations with portable output paths."""
    groups = {}

    def read_directory(directory, relative):
        for source in sorted(directory.iterdir(), key=lambda item: item.name):
            name = relative / source.name
            if source.is_dir():
                read_directory(source, name)
            elif source.name.endswith((".yaml", ".yml")):
                groups[name] = read_yaml(source)

    relative = BUNDLED_INCLUDES[name]
    resource = files("gramson.specs").joinpath(*relative.parts)
    if resource.is_dir():
        read_directory(resource, relative)
    else:
        groups[relative] = read_yaml(resource)
    groups = dict(sorted(groups.items()))
    merge_operators(groups)
    return groups


def load_core():
    """Load the default bundled core language."""
    return _load_bundled("gramson:core")


def merge_operators(groups):
    operators = {}
    operator_sources = {}
    definition_sources = {}
    for source, definitions in groups.items():
        try:
            generate_schema(definitions)
        except ValueError as error:
            raise ValueError(f"{source}: {error}") from error
        for name, definition in definitions.items():
            if name in operator_sources:
                raise ValueError(
                    f"Duplicate operator {name!r} in {operator_sources[name]} and {source}"
                )
            schema_name = definition.get("schemaName", f"operator_{name}")
            if schema_name in definition_sources:
                raise ValueError(
                    f"Duplicate schemaName {schema_name!r} in "
                    f"{definition_sources[schema_name]} and {source}"
                )
            operators[name] = definition
            operator_sources[name] = source
            definition_sources[schema_name] = source
    if not operators:
        raise ValueError("The language must contain at least one operator group.")
    return operators


def load_language(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = read_yaml(manifest_path)
    if not isinstance(manifest, dict) or set(manifest) - {"operatorDirectories", "include"}:
        raise ValueError(f"{manifest_path}: expected include and/or operatorDirectories.")
    includes = manifest.get("include", [])
    if not isinstance(includes, list):
        raise ValueError(f"{manifest_path}: include must be a list of bundled definition names.")
    groups = {}
    selected = set()
    for name in includes:
        if not isinstance(name, str) or name not in BUNDLED_INCLUDES:
            raise ValueError(f"{manifest_path}: unknown include {name!r}; expected one of {', '.join(BUNDLED_INCLUDES)}.")
        if name in selected:
            raise ValueError(f"{manifest_path}: repeated include {name!r}.")
        selected.add(name)
        groups.update(_load_bundled(name))
    directories = manifest.get("operatorDirectories", [])
    if not isinstance(directories, list) or (not directories and not groups):
        raise ValueError(f"{manifest_path}: operatorDirectories must be a nonempty list unless include selects bundled definitions.")
    source_root = manifest_path.parent
    sources = set()
    seen_directories = set()
    for directory in directories:
        if not isinstance(directory, str) or not directory.strip():
            raise ValueError(f"{manifest_path}: directory names must be nonempty strings.")
        relative = Path(directory)
        if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
            raise ValueError(f"{manifest_path}: directories must be relative subdirectories.")
        path = (source_root / relative).resolve()
        if not path.is_relative_to(source_root) or not path.is_dir():
            raise ValueError(f"{manifest_path}: missing or out-of-tree directory {directory!r}.")
        if path in seen_directories:
            raise ValueError(f"{manifest_path}: repeated directory {directory!r}.")
        seen_directories.add(path)
        operator_files = sorted(
            source for source in path.rglob("*")
            if source.is_file() and source.suffix in (".yaml", ".yml")
        )
        if not operator_files:
            raise ValueError(f"{manifest_path}: no YAML operator files in {directory!r}.")
        for source in operator_files:
            if not source.resolve().is_relative_to(source_root):
                raise ValueError(f"{source}: operator files must stay inside the specification.")
            sources.add(source)
    targets = {
        relative.with_suffix(".schema.yaml").as_posix().casefold(): f"bundled {relative}"
        for relative in groups
    }
    for source in sorted(sources):
        relative = source.relative_to(source_root)
        target = relative.with_suffix(".schema.yaml").as_posix().casefold()
        if target in targets:
            raise ValueError(f"Output collision between {targets[target]} and local {relative}.")
        targets[target] = relative
        groups[relative] = read_yaml(source)
    groups = dict(sorted(groups.items()))
    merge_operators(groups)
    return groups

def definition_reference(name, document=""):
    pointer_token = name.replace("~", "~0").replace("/", "~1")
    return f"{document}#/$defs/{quote(pointer_token, safe='')}"


def generate_schemas(groups):
    compiled = generate_schema(merge_operators(groups))
    dialect = compiled["$schema"]
    alternatives = [
        {"$ref": "shared.schema.yaml#/$defs/scalarLiteral"},
        {"$ref": "#/$defs/arrayExpression"},
    ]
    schemas = {
        Path("expression.schema.yaml"): {
            "$schema": dialect,
            "title": "Gramson expression grammar",
            "description": compiled["description"],
            "$ref": "#/$defs/expression",
            "$defs": {
                "expression": {"oneOf": alternatives},
                "arrayExpression": compiled["$defs"]["arrayExpression"],
            },
        },
        Path("shared.schema.yaml"): {
            "$schema": dialect,
            "title": "Shared expression definitions",
            "$defs": {"scalarLiteral": compiled["$defs"]["scalarLiteral"]},
        },
    }

    def relocate(value, expression_reference):
        if isinstance(value, list):
            return [relocate(item, expression_reference) for item in value]
        if isinstance(value, dict):
            return {
                key: (
                    expression_reference
                    if key == "$ref" and item == "#/$defs/expression"
                    else relocate(item, expression_reference)
                )
                for key, item in value.items()
            }
        return value

    for source, operators in groups.items():
        source = Path(source)
        if source.is_absolute() or ".." in source.parts:
            raise ValueError(f"{source}: expected a relative operator source path.")
        target = source.with_suffix(".schema.yaml")
        if target in schemas:
            raise ValueError(f"{source}: generated schema path collision at {target}.")
        expression_reference = quote(
            posixpath.relpath("expression.schema.yaml", target.parent.as_posix()), safe="/"
        ) + "#/$defs/expression"
        definitions = {}
        for name, operator in operators.items():
            schema_name = operator.get("schemaName", f"operator_{name}")
            definitions[schema_name] = relocate(
                compiled["$defs"][schema_name], expression_reference
            )
            alternatives.append({
                "$ref": definition_reference(schema_name, quote(target.as_posix(), safe="/"))
            })
        schemas[target] = {
            "$schema": dialect,
            "title": f"{source.stem} operators",
            "$defs": definitions,
        }
    return schemas


def write_schemas(schemas, output_directory):
    """Write an already compiled grammar without modifying unrelated files."""
    output_directory = Path(output_directory)
    for relative, schema in schemas.items():
        target = output_directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(schema, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
