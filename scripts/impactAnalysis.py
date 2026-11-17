from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


_EXCLUDED_DIRECTORIES = {
    ".auth",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "test-results",
}
_SHARED_PATHS = {
    ".env.example",
    "conftest.py",
    "pytest.ini",
    "requirements.txt",
}
_SHARED_DIRECTORIES = {".github", "data", "fixtures", "hooks", "utils"}


@dataclass(frozen=True)
class ImpactReport:
    changed_files: list[str]
    impacted_tests: list[str]
    scope: str


def _module_name(root: Path, source_path: Path) -> str:
    relative_path = source_path.relative_to(root)
    if relative_path.name == "__init__.py":
        return ".".join(relative_path.parent.parts)
    return ".".join(relative_path.with_suffix("").parts)


def _python_files(root: Path) -> list[Path]:
    files = []
    for current, directories, names in os.walk(root):
        directories[:] = sorted(
            name for name in directories if name not in _EXCLUDED_DIRECTORIES
        )
        files.extend(
            Path(current) / name for name in names if name.endswith(".py")
        )
    return files


def _imports_for_module(
    source: str, module_name: str, is_package: bool
) -> set[str]:
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                module_parts = (
                    module_name.split(".")
                    if is_package
                    else module_name.split(".")[:-1]
                )
                if node.level > 1:
                    module_parts = module_parts[: -(node.level - 1)]
                base = ".".join(
                    part for part in (*module_parts, node.module or "") if part
                )
            else:
                base = node.module or ""
            if base:
                imports.add(base)
                imports.update(
                    f"{base}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )
    return imports


def _build_dependency_graph(
    root: Path,
) -> tuple[dict[str, set[str]], dict[str, Path]]:
    source_paths = _python_files(root)
    modules = {_module_name(root, path): path for path in source_paths}
    graph: dict[str, set[str]] = {}
    for module_name, path in modules.items():
        imported_modules = _imports_for_module(
            path.read_text(encoding="utf-8"),
            module_name,
            path.name == "__init__.py",
        )
        dependencies: set[str] = set()
        for imported in imported_modules:
            candidate = imported
            while candidate and candidate not in modules:
                candidate = candidate.rpartition(".")[0]
            if candidate:
                dependencies.add(candidate)
        graph[module_name] = dependencies
    return graph, modules


def _test_case_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            names.extend(
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name.startswith("test")
            )
    return names


def _is_shared_change(path: str) -> bool:
    normalized = Path(path).as_posix()
    parts = Path(normalized).parts
    return normalized in _SHARED_PATHS or bool(
        parts and parts[0] in _SHARED_DIRECTORIES
    )


def analyze_impact(root: Path, changed_files: list[str]) -> ImpactReport:
    test_root = root / "testCases"
    test_files = sorted(test_root.rglob("test*.py"))
    if not test_files:
        raise FileNotFoundError(f"No pytest files found under {test_root}")

    graph, modules = _build_dependency_graph(root)
    changed_paths = {Path(path).as_posix() for path in changed_files}
    if any(_is_shared_change(path) for path in changed_paths):
        impacted_files = test_files
        broad_impact = True
    else:
        changed_modules = {
            _module_name(root, root / path)
            for path in changed_paths
            if path.endswith(".py") and (root / path).exists()
        }
        deleted_modules = {
            path
            for path in changed_paths
            if path.endswith(".py")
            and not (root / path).exists()
            and not path.startswith("testCases/")
        }
        broad_impact = bool(deleted_modules) or any(
            module not in modules for module in changed_modules
        )
        impacted_files = []
        for test_path in test_files:
            relative_test = test_path.relative_to(root).as_posix()
            test_module = _module_name(root, test_path)
            pending = [test_module]
            dependencies: set[str] = set()
            while pending:
                current = pending.pop()
                if current in dependencies:
                    continue
                dependencies.add(current)
                pending.extend(graph.get(current, ()))

            direct_change = relative_test in changed_paths
            dependency_change = any(
                dependency == changed
                or dependency.startswith(changed + ".")
                for dependency in dependencies
                for changed in changed_modules
            )
            if direct_change or dependency_change:
                impacted_files.append(test_path)

        if broad_impact:
            impacted_files = test_files

    impacted_tests = sorted(
        f"{_module_name(root, path)}::{name}"
        for path in impacted_files
        for name in _test_case_names(path)
    )
    scope = "all" if broad_impact else "targeted" if impacted_tests else "none"
    return ImpactReport(
        changed_files=sorted(changed_paths),
        impacted_tests=impacted_tests,
        scope=scope,
    )


def render_markdown(report: ImpactReport) -> str:
    lines = [
        "## Pull request impact analysis",
        "",
        f"**Impact scope:** {report.scope}",
        f"**Changed files:** {len(report.changed_files)}",
        f"**Impacted test cases:** {len(report.impacted_tests)}",
        "",
        "### Changed files",
    ]
    lines.extend(f"- `{path}`" for path in report.changed_files or ["None"])
    lines.extend(("", "### Impacted test cases"))
    lines.extend(f"- `{test}`" for test in report.impacted_tests or ["None"])
    lines.append("")
    return "\n".join(lines)


def _changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [path for path in result.stdout.splitlines() if path]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze pytest impact from files changed in a pull request."
    )
    parser.add_argument("--base", required=True, help="Base commit SHA or ref.")
    parser.add_argument("--head", required=True, help="Head commit SHA or ref.")
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    report = analyze_impact(root, _changed_files(args.base, args.head))
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    print(
        f"Impact analysis found {len(report.impacted_tests)} test cases "
        f"({report.scope} impact)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
