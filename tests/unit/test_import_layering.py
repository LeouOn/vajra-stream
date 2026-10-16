"""Phase 3 import-structure guard (docs/DEVELOPMENT_ROADMAP.md, "Consolidate").

Static (ast-only, nothing is imported) checks over the production packages:

1. **Layering.** Target: ``infrastructure``/``config`` <- ``core`` <- ``modules``
   <- ``backend``. A lower layer must not import a higher one at *module level*
   (inside ``if TYPE_CHECKING:`` is fine). A function-level import is the
   documented last resort and is not flagged here; each one carries a comment
   saying why it exists.
2. **No module-level import cycles** among the production modules (the
   packages above plus ``container.py`` and ``scripts/``, which the backend
   imports via ``backend/core/orchestrator_bridge.py``). Importing ``a.b.c``
   also runs ``a/__init__`` and ``a/b/__init__``, so those edges count too.
3. **No sys.path manipulation in production code.** The entry points put the
   project root on sys.path (``run.py``, uvicorn run from the root, pytest's
   rootdir, ``python -m``). ``run.py`` and ``scripts/*.py`` (run as files) may
   bootstrap it; a script that production code imports must guard its
   bootstrap with an ``if __package__ ...`` / ``if __name__ == "__main__"``
   check so importing it leaves sys.path alone.

The allow-lists below are explicit and empty. Shrink, never grow them: fix the
import (move shared code down a layer, invert the dependency, or make it a
commented function-level import) instead of adding an entry.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGES = ("infrastructure", "config", "core", "hardware", "modules", "backend", "scripts")
ROOT_MODULES = ("container",)
NO_SYS_PATH_PACKAGES = ("infrastructure", "config", "core", "hardware", "modules", "backend")

# Lower layers may not import the listed higher packages at module level.
FORBIDDEN_UPWARD: dict[str, tuple[str, ...]] = {
    "infrastructure": ("config", "core", "modules", "backend", "container", "scripts"),
    "config": ("infrastructure", "core", "modules", "backend", "container", "scripts"),
    "core": ("modules", "backend", "container", "scripts"),
    "modules": ("backend", "container", "scripts"),
    "hardware": ("backend", "container", "scripts"),
}

# (importing module, imported module) pairs tolerated at module level. Empty.
LAYERING_ALLOWLIST: frozenset[tuple[str, str]] = frozenset()
# Repo-relative paths allowed to mutate sys.path at module level, unguarded.
SYS_PATH_ALLOWLIST: frozenset[str] = frozenset({"run.py"})


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(REPO_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _production_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for pkg in PACKAGES:
        for path in (REPO_ROOT / pkg).rglob("*.py"):
            if "__pycache__" not in path.parts:
                files[_module_name(path)] = path
    for name in ROOT_MODULES:
        files[name] = REPO_ROOT / f"{name}.py"
    return files


FILES = _production_files()
PACKAGE_MODULES = {name for name, path in FILES.items() if path.name == "__init__.py"}
TREES = {name: ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for name, path in FILES.items()}


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _module_level_nodes(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Statements executed at import time: skips def bodies and TYPE_CHECKING blocks."""
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            yield from _module_level_nodes(node.orelse)
            continue
        yield node
        for field in ("body", "orelse", "finalbody", "handlers"):
            children = getattr(node, field, None)
            if isinstance(children, list):
                yield from _module_level_nodes([c for c in children if isinstance(c, ast.stmt | ast.excepthandler)])


def _resolve(name: str) -> str | None:
    parts = name.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in FILES:
            return candidate
        parts.pop()
    return None


def _module_level_imports(module: str) -> Iterator[tuple[str, int]]:
    """(first-party target module, line) for every import run at import time."""
    for node in _module_level_nodes(TREES[module].body):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve(alias.name)
                if target:
                    yield target, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = module.split(".")
                if module not in PACKAGE_MODULES:
                    base = base[:-1]
                base = base[: len(base) - (node.level - 1)]
                source = ".".join(base + ([node.module] if node.module else []))
            else:
                source = node.module or ""
            for alias in node.names:
                full = f"{source}.{alias.name}"
                target = full if full in FILES else _resolve(source)
                if target:
                    yield target, node.lineno


def _with_parents(target: str) -> list[str]:
    parts = target.split(".")
    return [p for p in (".".join(parts[:i]) for i in range(1, len(parts) + 1)) if p in FILES]


def _top(module: str) -> str:
    return module.split(".")[0]


def test_no_upward_module_level_imports():
    violations = []
    for module in FILES:
        forbidden = FORBIDDEN_UPWARD.get(_top(module), ())
        for target, line in _module_level_imports(module):
            if _top(target) in forbidden and (module, target) not in LAYERING_ALLOWLIST:
                violations.append(f"{FILES[module].relative_to(REPO_ROOT).as_posix()}:{line} imports {target}")
    assert not violations, (
        "module-level imports that point up the layering "
        "(infrastructure/config <- core <- modules <- backend):\n  " + "\n  ".join(sorted(violations))
    )


def _strongly_connected(graph: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[list[str]] = []
    counter = 0
    for root in sorted(graph):
        if root in index:
            continue
        work = [(root, iter(sorted(graph[root])))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, children = work[-1]
            child = next(children, None)
            if child is not None:
                if child not in index:
                    index[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, iter(sorted(graph[child]))))
                elif child in on_stack:
                    low[node] = min(low[node], index[child])
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                if len(component) > 1:
                    components.append(sorted(component))
    return components


def test_no_module_level_import_cycles():
    graph: dict[str, set[str]] = {module: set() for module in FILES}
    for module in FILES:
        for target, _line in _module_level_imports(module):
            for dep in _with_parents(target):
                # A module does not "import" the packages that contain it.
                if dep != module and not module.startswith(dep + "."):
                    graph[module].add(dep)
    cycles = _strongly_connected(graph)
    assert not cycles, "module-level import cycles:\n  " + "\n  ".join(" <-> ".join(c) for c in cycles)


def _is_sys_path_mutation(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            owner = func.value
            if (
                func.attr in {"insert", "append", "extend"}
                and isinstance(owner, ast.Attribute)
                and owner.attr == "path"
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "sys"
            ):
                return True
            if func.attr == "addsitedir" and isinstance(owner, ast.Name) and owner.id == "site":
                return True
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AugAssign):
        targets = [node.target]
    for target in targets:
        if isinstance(target, ast.Subscript):
            target = target.value
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "path"
            and isinstance(target.value, ast.Name)
            and target.value.id == "sys"
        ):
            return True
    return False


def _guarded_by_script_check(test: ast.expr) -> bool:
    names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
    return bool(names & {"__package__", "__name__"})


def _unguarded_sys_path_lines(tree: ast.Module) -> list[int]:
    lines: list[int] = []

    def visit(node: ast.AST, guarded: bool) -> None:
        if isinstance(node, ast.If) and _guarded_by_script_check(node.test):
            for child in node.body:
                visit(child, True)
            for child in node.orelse:
                visit(child, guarded)
            return
        if _is_sys_path_mutation(node) and not guarded:
            lines.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child, guarded)

    visit(tree, False)
    return sorted(set(lines))


def test_no_sys_path_manipulation_in_production_code():
    offenders = []
    for module, path in FILES.items():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if _top(module) not in NO_SYS_PATH_PACKAGES and module not in ROOT_MODULES:
            continue
        if rel in SYS_PATH_ALLOWLIST:
            continue
        offenders += [f"{rel}:{line}" for line in _unguarded_sys_path_lines(TREES[module])]
    assert not offenders, (
        "sys.path manipulation in production code (the entry point puts the project root "
        "on sys.path; import modules by their package path instead):\n  " + "\n  ".join(offenders)
    )


def test_scripts_imported_by_production_do_not_touch_sys_path_on_import():
    imported_scripts = set()
    for module in FILES:
        if _top(module) == "scripts":
            continue
        for node in ast.walk(TREES[module]):
            if isinstance(node, ast.ImportFrom) and node.module and _top(node.module) == "scripts":
                target = _resolve(node.module)
                if target:
                    imported_scripts.add(target)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _top(alias.name) == "scripts" and _resolve(alias.name):
                        imported_scripts.add(_resolve(alias.name))
    offenders = [
        f"{FILES[s].relative_to(REPO_ROOT).as_posix()}:{line}"
        for s in sorted(imported_scripts)
        for line in _unguarded_sys_path_lines(TREES[s])
    ]
    assert not offenders, (
        "a script that production code imports mutates sys.path on import; guard the "
        "bootstrap with `if __package__ in (None, ''):`:\n  " + "\n  ".join(offenders)
    )


def test_guard_sees_known_shapes():
    """The detectors catch the spellings this repo used to have."""
    samples = {
        "sys.path.insert(0, str(Path(__file__).parent.parent))": True,
        "sys.path.append(os.path.dirname(__file__))": True,
        "sys.path[:0] = ['x']": True,
        "sys.path += ['x']": True,
        "site.addsitedir('x')": True,
        "if __package__ in (None, ''):\n    sys.path.insert(0, 'x')": False,
        "print(sys.path)": False,
    }
    for source, flagged in samples.items():
        assert bool(_unguarded_sys_path_lines(ast.parse(source))) is flagged, source

    upward = ast.parse("try:\n    from backend.x import y\nexcept ImportError:\n    y = None\n")
    assert [type(n).__name__ for n in _module_level_nodes(upward.body)].count("ImportFrom") == 1
    deferred = ast.parse("def f():\n    from backend.x import y\nif TYPE_CHECKING:\n    import backend\n")
    assert not [n for n in _module_level_nodes(deferred.body) if isinstance(n, ast.Import | ast.ImportFrom)]
