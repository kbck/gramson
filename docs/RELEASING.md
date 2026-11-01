# Releasing Gramson

The initial package version is `0.1.0`. Preparation and local checks do not upload
anything. Publishing a GitHub release triggers the PyPI workflow described below.

## Build and verify locally

From a clean checkout of the release commit, with no old artifacts in `dist/`:

```sh
make setup-release
make check
make check-dist
```

`make check-dist` builds both `dist/gramson-0.1.0.tar.gz` and
`dist/gramson-0.1.0-py3-none-any.whl`. The wheel is built from the source
distribution, rather than directly from the checkout. It then checks:

- PyPI metadata and description rendering with `twine check --strict`.
- All generated schema files, byte-for-byte, in the wheel and source archive.
- The complete specification, generator, tests, fixtures, and user documentation
  in the source archive. This maintainer release guide stays in the repository
  and is explicitly excluded from both distributions.
- The CLI entry point, MIT license, and third-party notices in the wheel.
- JSON and YAML validation, plus rejection of an unknown operator, from an
  installed wheel outside the checkout. This smoke test installs with `--no-deps`
  and uses the release environment's existing dependencies.

Inspect the archives and `docs/PYPI.md`, which supplies the PyPI description.
CI runs these checks on pushes and pull requests with Python 3.10 and 3.14.
Generated schemas must already be committed; release checks do not regenerate them.

## Configure PyPI once

1. Sign in to PyPI with an account permitted to publish the project.
2. For the first release, configure a
   [pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
   with these values:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `gramson` |
   | GitHub owner | `kbck` |
   | GitHub repository | `gramson` |
   | Workflow filename | `publish.yml` |
   | Environment | `pypi` |

   For an existing project, add the same publisher under its publishing settings.
   A pending publisher does not reserve the package name.
3. Create the `pypi` environment in the GitHub repository settings. Restrict its
   deployment tags to `v*` and optionally configure required reviewers.

The workflow uses PyPI Trusted Publishing with GitHub OIDC. No long-lived PyPI
API token needs to be stored in GitHub secrets. See
[PyPI's publishing instructions](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Publish a release

1. Set the intended version in `pyproject.toml`, update the release notes, and
   commit the verified source and generated schemas. Use a new version for every
   upload; published distribution files cannot be replaced.
2. Confirm the Check workflow passed for that commit.
3. Create a GitHub release with the exact matching tag, initially `v0.1.0`,
   pointing to that commit. Publishing the release starts
   [publish.yml](../.github/workflows/publish.yml).
4. The workflow verifies the tag/version match, reruns tests, builds and checks
   both archives, then passes those exact archives to a separate publishing job.
   Only that job can request the OIDC token. Approve its deployment if reviewers
   were configured for the `pypi` environment.
5. After publication, inspect <https://pypi.org/project/gramson/> and test in a new
   virtual environment:

   ```sh
   python -m pip install gramson==0.1.0
   printf '%s\n' '{"var":"price"}' | gramson validate -
   ```

The repository preparation does not configure accounts, create a tag or release,
or publish either archive.
