# PyPI release checklist

Great Generator publishes to PyPI through GitHub Actions and PyPI Trusted Publishing. No PyPI API token is required when Trusted Publisher is configured correctly.

## Package identity

- PyPI project/package name: `great-generator`
- Python import name: `great_generator`
- GitHub repository: `GreatDataLabs/great-generator`
- Current release version: `0.1.8`

## One-time PyPI Trusted Publisher setup

The PyPI project must have a Trusted Publisher entry that matches the current GitHub owner/repository. After moving the repository into the GreatDataLabs organization, verify or recreate the publisher with the values below before publishing from the org repo.

On PyPI, go to **Publishing** / **Trusted Publishers** and add a pending publisher with these exact values:

```text
Project name: great-generator
Owner: GreatDataLabs
Repository name: great-generator
Workflow name: release-pypi.yml
Environment name: pypi
```

For TestPyPI, add a pending publisher with:

```text
Project name: great-generator
Owner: GreatDataLabs
Repository name: great-generator
Workflow name: release-testpypi.yml
Environment name: testpypi
```

Notes:

- `Owner` must be the GitHub owner/login, not the display name.
- Use `GreatDataLabs`, not `Ravi Kiran Pagidi`, because Trusted Publishing expects the GitHub owner/login.
- The screenshot showing GitHub under PyPI account associations is helpful, but it is not the same thing as a pending Trusted Publisher entry.
- The GitHub workflow uses `environment: pypi`, which is required for the OIDC identity PyPI checks.

## Before every release

1. Confirm the version in:
   - `pyproject.toml`
   - `great_generator/__init__.py`
2. Confirm `CHANGELOG.md` has the release notes for the version.
3. Run local checks:

```bash
ruff check .
black --check .
pytest
python -m build
python -m twine check dist/*
```

4. Optional clean-wheel smoke test:

```bash
python -m venv .release-smoke
.release-smoke\Scripts\activate
python -m pip install --upgrade pip
python -m pip install dist\great_generator-*.whl
python - <<'PY'
from great_generator import generate_domain

data = generate_domain("ecommerce", scale="tiny", realism="realistic", seed=42)
assert len(data["customers"]) == 25
print("smoke test passed")
PY
```

On macOS/Linux, activate with:

```bash
source .release-smoke/bin/activate
```

## Recommended production release flow

### 1. Optional TestPyPI dry run

Run the `publish-testpypi` workflow manually from GitHub Actions.

After it succeeds, test install from TestPyPI:

```bash
python -m venv .testpypi-smoke
.testpypi-smoke\Scripts\activate
python -m pip install --upgrade pip
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ great-generator
python - <<'PY'
from great_generator import generate_domain

data = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
assert len(data["customers"]) == 25
print("TestPyPI install passed")
PY
```

### 2. Production PyPI release

Recommended path:

1. Push all release-ready changes to `main`.
2. Confirm the version has not already been published on PyPI.
3. Create and push a version tag, for example `v0.1.8`.
4. GitHub Actions runs `.github/workflows/release-pypi.yml` and publishes to PyPI through Trusted Publishing.
5. Optionally create a GitHub release from the same tag using the matching release-notes document, such as `docs/RELEASE_0_1_8.md`.

Alternative path:

- Run the `publish-pypi` workflow manually from GitHub Actions after the Trusted Publisher entry exists.

## Post-release verification

After PyPI publish succeeds:

```bash
python -m venv .pypi-smoke
.pypi-smoke\Scripts\activate
python -m pip install --upgrade pip
python -m pip install great-generator
python - <<'PY'
from great_generator import generate_domain, list_domains

assert "banking" in list_domains()
data = generate_domain("banking", scale="tiny", realism="realistic", seed=42)
assert len(data["customers"]) == 25
print("PyPI install passed")
PY
```

Then verify:

- PyPI project page renders README correctly.
- GitHub release links to the right tag.
- README badges resolve.
- Wiki and documentation links work.

## If publishing fails

Common causes:

- PyPI pending Trusted Publisher was not added.
- Owner/repository/workflow/environment values do not exactly match.
- The version already exists on PyPI. PyPI versions cannot be overwritten.
- The GitHub release was created from the wrong branch or commit.
- The package name is already taken.
