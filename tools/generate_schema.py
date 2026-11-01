"""Repository entry point; the reusable generator lives in gramson.generation."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))

# Keep existing imports from tools.generate_schema working.
from gramson.generation import (
    UniqueKeyLoader, definition_reference, generate_schema, generate_schemas,
    load_language, merge_operators, read_yaml,
)


if __name__ == "__main__":
    from gramson.cli import main

    raise SystemExit(main([
        "generate", "--manifest", str(ROOT / "spec" / "language.yaml"),
        "--output-directory", str(ROOT / "schema"), *sys.argv[1:],
    ]))
