"""Check release artifacts and smoke-test the wheel outside the checkout."""

import argparse
from configparser import ConfigParser
from email.parser import Parser
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ONLY = {"docs/RELEASING.md"}


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    name, version = project["name"], project["version"]
    wheel = options.directory / f"{name}-{version}-py3-none-any.whl"
    sdist = options.directory / f"{name}-{version}.tar.gz"
    require(
        set(options.directory.glob("*")) == {wheel, sdist},
        f"Expected only {wheel.name} and {sdist.name}; use an empty dist directory for each release.",
    )
    subprocess.run([sys.executable, "-m", "twine", "check", "--strict", str(wheel), str(sdist)], check=True)

    schemas = {
        path.relative_to(ROOT / "schema").as_posix(): path.read_bytes()
        for path in (ROOT / "schema").rglob("*.schema.yaml")
    }
    with ZipFile(wheel) as archive:
        require(
            not any(Path(path).name == "RELEASING.md" for path in archive.namelist()),
            "Maintainer release instructions must not be included in the wheel.",
        )
        bundled = {
            path.removeprefix("gramson/schemas/"): archive.read(path)
            for path in archive.namelist()
            if path.startswith("gramson/schemas/") and path.endswith(".schema.yaml")
        }
        require(bundled == schemas, "Wheel schemas differ from the committed generated schemas.")
        metadata = Parser().parsestr(archive.read(f"{name}-{version}.dist-info/METADATA").decode())
        require(metadata["Name"] == name and metadata["Version"] == version, "Unexpected wheel metadata.")
        require(metadata["License-Expression"] == "MIT", "Missing MIT license metadata.")
        entry_points = ConfigParser()
        entry_points.read_string(archive.read(f"{name}-{version}.dist-info/entry_points.txt").decode())
        require(entry_points["console_scripts"]["gramson"] == "gramson.cli:main", "Missing CLI entry point.")
        for path in project["license-files"]:
            require(
                archive.read(f"{name}-{version}.dist-info/licenses/{path}") == (ROOT / path).read_bytes(),
                f"Wheel license or notice differs: {path}",
            )

    required = {
        "pyproject.toml", "MANIFEST.in", "README.md", "Makefile",
        "requirements-dev.txt", "requirements-release.txt", *project["license-files"],
    }
    for directory in ("gramson", "schema", "spec", "tools", "tests", "examples", "docs"):
        required.update(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / directory).rglob("*")
            if path.is_file() and (path.suffix in (".py", ".yaml", ".yml", ".json", ".md", ".html") or path.name == "LICENSE")
        )
    with tarfile.open(sdist, "r:gz") as archive:
        for path in REPOSITORY_ONLY:
            require(
                f"{name}-{version}/{path}" not in archive.getnames(),
                f"Repository-only file must not be included in the source distribution: {path}",
            )
        for path in sorted(required - REPOSITORY_ONLY):
            member = archive.extractfile(f"{name}-{version}/{path}")
            require(member is not None and member.read() == (ROOT / path).read_bytes(), f"Source distribution differs: {path}")

    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        installed = directory / "installed"
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--no-deps", "--no-index",
            "--target", str(installed), str(wheel.resolve()),
        ], check=True, capture_output=True, text=True)
        launcher = """
import pathlib, runpy, sys
installed = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
import gramson
if not pathlib.Path(gramson.__file__).resolve().is_relative_to(installed):
    raise SystemExit('Imported the checkout instead of the installed wheel.')
sys.argv = ['gramson', 'validate', sys.argv[2]]
runpy.run_module('gramson', run_name='__main__')
"""
        for filename, contents, expected in (
            ("expression.json", '{"+": [{"var": "price"}, 1]}', 0),
            ("expression.yaml", "if: [true, {var: price}, 0]\n", 0),
            ("invalid.json", '{"unknown": []}', 1),
        ):
            (directory / filename).write_text(contents)
            result = subprocess.run(
                [sys.executable, "-I", "-c", launcher, str(installed), filename],
                cwd=directory, capture_output=True, text=True,
            )
            require(result.returncode == expected, result.stdout + result.stderr)
    print(f"Verified {name} {version}: metadata, licenses, {len(schemas)} bundled schemas, source files, and installed CLI.")


if __name__ == "__main__":
    main()
