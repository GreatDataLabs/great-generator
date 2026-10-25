"""Validate this repository's portable skill bundle (requires the existing dev extra)."""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "schema-test-data",
    "query-test-data",
    "relational-test-fixtures",
    "data-pipeline-test-pack",
    "schema-change-regression",
    "databricks-test-data",
)


def validate(root=ROOT):
    errors = []
    found = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    if found != set(SKILLS):
        errors.append(f"Expected six workflow skills; found {sorted(found)}")
    for name in SKILLS:
        directory = root / "skills" / name
        path = directory / "SKILL.md"
        if not path.exists():
            errors.append(f"Missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            errors.append(f"{path}: YAML frontmatter required")
            continue
        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            errors.append(f"{path}: {exc}")
            continue
        if not isinstance(metadata, dict):
            errors.append(f"{path}: frontmatter must be a mapping")
            continue
        if (
            metadata.get("name") != name
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or len(name) > 64
        ):
            errors.append(f"{path}: invalid/mismatched name")
        for field, maximum in (("description", 1024), ("compatibility", 500)):
            value = metadata.get(field, "")
            if not isinstance(value, str) or not 0 < len(value) <= maximum:
                errors.append(f"{path}: {field} must contain 1..{maximum} characters")
        if "allowed-tools" in metadata:
            errors.append(f"{path}: this bundle must not pre-approve tools")
        if len(parts[2].splitlines()) > 200:
            errors.append(f"{path}: move lengthy detail to references")
        if not list((directory / "references").glob("*.md")) or not list(
            (directory / "examples").glob("*.py")
        ):
            errors.append(f"{path}: references and executable examples are required")
        for document in directory.rglob("*.md"):
            for target in re.findall(
                r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")
            ):
                if target.startswith(("https://", "http://", "#")):
                    continue
                destination = (document.parent / target.split("#", 1)[0]).resolve()
                if not destination.is_relative_to(directory.resolve()) or not destination.is_file():
                    errors.append(f"{document}: missing/non-portable resource link {target}")
        for script in directory.rglob("*.py"):
            try:
                tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
                compile(tree, str(script), "exec")
            except SyntaxError as exc:
                errors.append(f"{script}: {exc}")
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("great_generator")
                ):
                    module = importlib.import_module(node.module)
                    for alias in node.names:
                        if not hasattr(module, alias.name):
                            errors.append(f"{script}: nonexistent API {node.module}.{alias.name}")
    return errors


if __name__ == "__main__":
    problems = validate()
    if problems:
        raise SystemExit("\n".join(problems))
    print("Six skills validated: metadata, resource links, syntax and imported package APIs.")
