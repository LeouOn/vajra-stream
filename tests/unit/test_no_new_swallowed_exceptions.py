"""IR-8: a DOWNWARD-ONLY ratchet for swallowed exceptions.

The recurring root cause of this project's silent failures is a swallowed
exception: ``except Exception: pass`` hides a dead feature behind a log line
nobody reads. Today lint cannot see it -- the project's ruff ``select`` is
``E F W I UP``, and the production tree carries dozens of silent
``except ...: pass`` blocks and hundreds of blind excepts.

This test freezes the CURRENT counts as an upper bound, per file and per rule:

* it FAILS if any file/rule count EXCEEDS its baseline, or if a file/rule
  appears that is not in the baseline at all;
* it does NOT fail when counts go DOWN, so the IR-1..IR-7 fix tickets can
  remove swallows without ever editing this baseline, and cannot conflict with
  each other over it;
* a second, informational test prints the current total so progress is visible.

The counts come from ruff itself, run with an ISOLATED configuration for ONLY
these three rules -- so the project's own lint configuration is never touched
and ``ruff check .`` in CI keeps passing on the existing debt:

    .venv/bin/python -m ruff check --isolated \\
        --select S110,BLE001,SIM105 --output-format json <paths>

* ``S110``    try-except-pass: the swallow itself.
* ``BLE001``  blind except: ``except Exception`` / ``except BaseException``.
* ``SIM105``  contextlib.suppress: the same intent, spelled differently.

This test does not import core/backend, needs no network, no database and no
API key, and runs in well under a second.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "swallowed_exceptions_baseline.json"

#: The production code the ratchet covers. Tests, docs and scratch trees are
#: deliberately excluded: the ratchet exists to stop PRODUCTION code from
#: hiding failures, and including the test suite would make the baseline churn
#: with every test that is added or rewritten.
SCAN_PATHS: tuple[str, ...] = (
    "core",
    "backend",
    "modules",
    "infrastructure",
    "config",
    "scripts",
    "container.py",
)

#: The rules counted. S110 is the swallow, BLE001 the blind except, SIM105 the
#: contextlib spelling of the same intent.
RULES: tuple[str, ...] = ("S110", "BLE001", "SIM105")

#: The one-line command that regenerates the baseline AFTER counts have gone
#: down. It never raises a count: ``build_baseline`` keeps min(current,
#: baseline) and refuses to introduce a file/rule that is not already in the
#: baseline, so running it can only ever burn debt down. To add a NEW file or
#: rule you must edit the JSON by hand, with a justification.
REGENERATE_COMMAND = (
    ".venv/bin/python -c \"import json,sys;sys.path.insert(0,'tests/unit');"
    "import test_no_new_swallowed_exceptions as t;from pathlib import Path;"
    "Path('tests/fixtures/swallowed_exceptions_baseline.json').write_text("
    "json.dumps(t.build_baseline(),indent=2,sort_keys=True)+'\\n')\""
)


def _ruff_module() -> str:
    """The ruff available to THIS interpreter, or skip."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        pytest.skip(f"ruff is not runnable through this interpreter: {exc}")
    if proc.returncode != 0:  # pragma: no cover
        pytest.skip(f"ruff is not available through this interpreter: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _collect(root: Path = PROJECT_ROOT, paths: tuple[str, ...] = SCAN_PATHS) -> dict[str, dict[str, int]]:
    """Count the findings per file and per rule under ``root``.

    Returns ``{"<path relative to root>": {"<rule>": <count>}}``. A file with no
    findings is absent rather than present-with-zeros.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            "--select",
            ",".join(RULES),
            "--output-format",
            "json",
            *paths,
        ],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=str(root),
    )
    if proc.returncode not in (0, 1):
        # ruff exits 1 when it reports findings, 0 when clean. Anything else is
        # a real failure (bad path, bad rule) and must not be read as "clean".
        raise AssertionError(
            f"ruff failed with exit code {proc.returncode} (expected 0 or 1).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    try:
        findings = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise AssertionError(f"ruff did not emit JSON: {exc}\nstdout:\n{proc.stdout}") from exc

    counts: dict[str, dict[str, int]] = {}
    for item in findings:
        absolute = Path(item["filename"])
        try:
            relative = absolute.relative_to(root)
        except ValueError:  # pragma: no cover
            relative = absolute
        code = item.get("code") or "unknown"
        counts.setdefault(relative.as_posix(), {})
        counts[relative.as_posix()][code] = counts[relative.as_posix()].get(code, 0) + 1
    return counts


def _violations(actual: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> list[str]:
    """The ways in which ``actual`` has grown beyond ``baseline``.

    Growth is a violation; a REDUCTION is not. A file or rule that is not in
    the baseline at all is a violation, because it is new debt.
    """
    problems: list[str] = []
    for path, rules in sorted(actual.items()):
        known = baseline.get(path)
        if known is None:
            problems.append(f"NEW FILE {path}: {rules} was not in the baseline at all")
            continue
        for code, count in sorted(rules.items()):
            allowed = known.get(code, 0)
            if count > allowed:
                problems.append(f"GREW {path} [{code}]: {count} > baseline {allowed} " f"(+{count - allowed})")
    return problems


def _totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    """Total findings per rule across every file."""
    totals = {rule: 0 for rule in RULES}
    for rules in counts.values():
        for code, count in rules.items():
            totals[code] = totals.get(code, 0) + count
    return totals


def _load_baseline() -> dict[str, dict[str, int]]:
    if not BASELINE_PATH.exists():
        # The baseline does not exist yet: this is the FIRST generation, not a
        # regression. build_baseline() handles that case; the ratchet test
        # below fails loudly, because a missing baseline means nothing is
        # frozen.
        return {}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {str(k): {str(c): int(n) for c, n in v.items()} for k, v in data["counts"].items()}


def build_baseline(allow_increase: bool = False) -> dict:
    """A baseline built from the current tree, that can only ever go DOWN.

    With ``allow_increase=False`` (the default, and what the documented
    regeneration command uses) the result keeps ``min(current, baseline)`` for
    every file/rule already in the baseline, drops files that no longer exist,
    and REFUSES to add a file or rule that is not already in the baseline.
    That makes the regeneration command safe: it cannot be used to quietly
    paper over a new swallow.
    """
    current = _collect()
    existing = _load_baseline()
    if not existing:
        # FIRST generation: the baseline is whatever the tree has today.
        return {
            "_comment": (
                "Upper bounds for swallowed exceptions in production code. Counts may "
                "go DOWN freely; going up fails tests/unit/test_no_new_swallowed_exceptions.py. "
                "Regenerate downwards with: " + REGENERATE_COMMAND
            ),
            "rules": list(RULES),
            "scan_paths": list(SCAN_PATHS),
            "counts": current,
        }
    merged: dict[str, dict[str, int]] = {}
    for path, rules in current.items():
        known = existing.get(path)
        if known is None:
            if not allow_increase:
                raise AssertionError(
                    f"refusing to add {path} to the baseline: it is not in the baseline "
                    f"and {rules} is new debt. Fix the swallowed exception instead, or "
                    f"edit the JSON by hand with a justification."
                )
            merged[path] = dict(rules)
            continue
        kept: dict[str, int] = {}
        for code, count in rules.items():
            allowed = known.get(code, 0)
            if count > allowed and not allow_increase:
                raise AssertionError(
                    f"refusing to raise {path} [{code}] from {allowed} to {count}: "
                    f"the baseline only ever goes down."
                )
            kept[code] = min(count, allowed)
        merged[path] = kept
    return {
        "_comment": (
            "Upper bounds for swallowed exceptions in production code. Counts may "
            "go DOWN freely; going up fails tests/unit/test_no_new_swallowed_exceptions.py. "
            "Regenerate downwards with: " + REGENERATE_COMMAND
        ),
        "rules": list(RULES),
        "scan_paths": list(SCAN_PATHS),
        "counts": merged,
    }


# ---------------------------------------------------------------------------
# the ratchet
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_new_swallowed_exceptions() -> None:
    """No file and no rule may exceed its frozen baseline.

    A file/rule that is not in the baseline at all also fails: that is new
    debt, and the ratchet is exactly the thing that stops it appearing.
    """
    _ruff_module()
    actual = _collect()
    baseline = _load_baseline()
    problems = _violations(actual, baseline)

    assert not problems, (
        "Swallowed exceptions grew. The ratchet is DOWNWARD-ONLY: the fix is to "
        "stop swallowing the exception (log it with exc_info=True, or let it "
        "raise), never to raise the baseline.\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\n\nCurrent totals: "
        + ", ".join(f"{k}={v}" for k, v in sorted(_totals(actual).items()))
    )


@pytest.mark.unit
def test_swallowed_exception_total_is_reported() -> None:
    """Informational: print the current totals so progress is visible.

    This never fails. It exists so a reviewer can see the debt shrinking
    without diffing the baseline JSON.
    """
    _ruff_module()
    actual = _collect()
    totals = _totals(actual)
    total = sum(totals.values())
    print(
        f"swallowed exceptions in production code: {total} total "
        f"({', '.join(f'{k}={v}' for k, v in sorted(totals.items()))}) "
        f"across {len(actual)} files"
    )
    assert total >= 0


# ---------------------------------------------------------------------------
# the detector itself, proven in a tmp_path copy
# ---------------------------------------------------------------------------


def _make_tree(root: Path) -> None:
    """A miniature production tree with the same shape as the real one."""
    for relative in SCAN_PATHS:
        target = root / relative
        if relative.endswith(".py"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "def helper():\n" "    try:\n" "        return 1\n" "    except Exception:\n" "        pass\n",
                encoding="utf-8",
            )
        else:
            target.mkdir(parents=True, exist_ok=True)
            (target / "module.py").write_text(
                "def helper():\n" "    try:\n" "        return 1\n" "    except Exception:\n" "        pass\n",
                encoding="utf-8",
            )


@pytest.mark.unit
def test_ratchet_detects_a_new_swallow_and_tolerates_a_removal(tmp_path: Path) -> None:
    """Prove the ratchet can actually fail, and that going down is allowed.

    Without this, a ratchet whose comparison logic was accidentally broken
    (always returning "no violations") would pass forever and protect nothing.
    """
    _ruff_module()
    tree = tmp_path / "repo"
    tree.mkdir()
    _make_tree(tree)

    baseline = _collect(tree)
    assert baseline, "the miniature tree should produce findings to start from"

    # 1. nothing has changed -> no violations.
    assert _violations(_collect(tree), baseline) == []

    # 2. a NEW swallowed exception appears -> the ratchet must notice.
    victim = tree / "core" / "new_swallow.py"
    victim.write_text(
        "def swallow():\n" "    try:\n" "        return 1\n" "    except Exception:\n" "        pass\n",
        encoding="utf-8",
    )
    grown = _collect(tree)
    problems = _violations(grown, baseline)
    assert problems, "a new swallowed exception must be reported"
    assert any("NEW FILE" in p for p in problems), problems

    # 3. and it must be reported as growth for an EXISTING file too.
    #    The second swallow has to be a SEPARATE try statement: a second
    #    ``except`` clause on the same try is still one S110 finding.
    victim.unlink()
    existing = tree / "core" / "module.py"
    existing.write_text(
        "def helper():\n"
        "    try:\n"
        "        return 1\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "def helper_two():\n"
        "    try:\n"
        "        return 2\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )
    problems = _violations(_collect(tree), baseline)
    assert problems, "a second swallow in a known file must be reported"
    assert any("GREW" in p for p in problems), problems

    # 4. going DOWN is always allowed: removing a swallow must not fail.
    existing.write_text(
        "def helper():\n" "    return 1\n",
        encoding="utf-8",
    )
    reduced = _collect(tree)
    assert _violations(reduced, baseline) == [], "a reduction must never fail the ratchet"
    assert sum(sum(r.values()) for r in reduced.values()) < sum(sum(r.values()) for r in baseline.values())
