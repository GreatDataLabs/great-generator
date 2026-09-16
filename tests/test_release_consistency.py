from pathlib import Path

import great_generator


def _pyproject_version() -> str:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("pyproject.toml does not define project version")


def test_pyproject_version_matches_package_version():
    assert _pyproject_version() == great_generator.__version__


def test_changelog_contains_current_version():
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## {great_generator.__version__}" in changelog
