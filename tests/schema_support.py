import json

import yaml
from referencing import Registry, Resource


def read_schemas(directory):
    schemas = {}
    for path in sorted(directory.rglob("*.schema.*")):
        if path.suffix == ".yaml":
            schemas[path.relative_to(directory)] = yaml.safe_load(path.read_text(encoding="utf-8"))
        elif path.suffix == ".json":
            schemas[path.relative_to(directory)] = json.loads(path.read_text(encoding="utf-8"))
    return schemas


def schema_registry(schemas, directory):
    return Registry().with_resources(
        ((directory / relative).as_uri(), Resource.from_contents(schema))
        for relative, schema in schemas.items()
    )
