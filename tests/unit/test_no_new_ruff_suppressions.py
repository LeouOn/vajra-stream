"""Wave 5 Task 30 — Freeze ruff ``per-file-ignores`` baseline.

Guards Guardrail G10 and the Metis deferred-suppression trap: once a
remediation wave has burned down ruff violations, the debt must not
silently re-accumulate via new ``per-file-ignores`` entries or new
rule codes appended to existing entries.

This test snapshots BOTH axes of the ``[tool.ruff.lint.per-file-ignores]``
table in ``pyproject.toml``:

* the number of file-pattern entries (keys), and
* the total number of rule-code suppressions across all entries
  (sum of len(value) for every key).

Reduction is always allowed — the snapshots are upper bounds. Any
increase fails the test, forcing the author to either fix the
underlying lint error or explicitly raise the baseline here (which
is itself a visible, reviewable signal).

If you genuinely need to raise the baseline, update the two
``*_MAX`` constants below AND add a justification comment referencing
the remediation/trade-off that warranted it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# tomllib landed in the stdlib in Python 3.11; fall back to the ``tomli``
# backport (and finally to ``toml``) so this test runs on 3.10 too.
# ---------------------------------------------------------------------------
try:  # pragma: no cover — exercised only on 3.11+
    import tomllib as _toml_lib
except ModuleNotFoundError:  # pragma: no cover — exercised only on 3.10
    try:
        import tomli as _toml_lib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover — last-resort fallback
        import toml as _toml_lib  # type: ignore[no-redef,assignment]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

# ---------------------------------------------------------------------------
# FROZEN BASELINE — remediation-30 (Guardrail G10)
# ---------------------------------------------------------------------------
# These are UPPER BOUNDS. Reductions are welcome; increases are not.
# To raise them you must (a) justify why a new suppression is unavoidable,
# (b) update the constant, and (c) reference the decision in the commit.
PER_FILE_IGNORES_ENTRY_MAX = 11      # number of file-pattern keys
PER_FILE_IGNORES_RULE_MAX = 22       # total rule codes across all entries


def _load_per_file_ignores() -> dict[str, list[str]]:
    """Parse ``[tool.ruff.lint.per-file-ignores]`` from pyproject.toml.

    Returns a mapping of file-pattern -> list of rule-code strings.
    """
    with PYPROJECT.open("rb") as fh:
        raw = fh.read()
    # tomllib / tomli take bytes; the legacy ``toml`` package takes text.
    if hasattr(_toml_lib, "loads"):
        try:
            data = _toml_lib.loads(raw.decode("utf-8"))  # type: ignore[attr-defined]
        except TypeError:
            data = _toml_lib.loads(raw)  # type: ignore[attr-defined]
    else:  # pragma: no cover — ``toml`` fallback path
        data = _toml_lib.loads(raw.decode("utf-8"))  # type: ignore[attr-defined]

    table = (
        data.get("tool", {})
        .get("ruff", {})
        .get("lint", {})
        .get("per-file-ignores", {})
    )
    if not isinstance(table, dict):
        pytest.fail(
            "[tool.ruff.lint.per-file-ignores] is missing or not a table "
            "in pyproject.toml — has the schema changed?"
        )
    return {str(k): list(v) for k, v in table.items()}


@pytest.mark.unit
def test_per_file_ignores_entry_count_frozen() -> None:
    """Number of file-pattern entries must not exceed the frozen baseline."""
    table = _load_per_file_ignores()
    actual = len(table)
    assert actual <= PER_FILE_IGNORES_ENTRY_MAX, (
        f"ruff per-file-ignores grew: {actual} entries > "
        f"frozen max {PER_FILE_IGNORES_ENTRY_MAX}.\n"
        "Guardrail G10 forbids new suppressions. Either fix the underlying "
        "lint error, or — if genuinely unavoidable — raise "
        "PER_FILE_IGNORES_ENTRY_MAX in this test with a justification and "
        "a reference to the remediation/decision.\n"
        f"Current entries:\n  - " + "\n  - ".join(sorted(table))
    )


@pytest.mark.unit
def test_per_file_ignores_rule_count_frozen() -> None:
    """Total rule-code suppressions must not exceed the frozen baseline.

    This catches the sneakier failure mode where someone appends a new
    rule code to an *existing* file-pattern entry without adding a new
    key (which the entry-count test above would miss).
    """
    table = _load_per_file_ignores()
    actual = sum(len(rules) for rules in table.values())
    assert actual <= PER_FILE_IGNORES_RULE_MAX, (
        f"ruff per-file-ignores rule total grew: {actual} rule codes > "
        f"frozen max {PER_FILE_IGNORES_RULE_MAX}.\n"
        "Guardrail G10 forbids new suppressions — including appending new "
        "rule codes to existing file patterns. Fix the underlying lint "
        "error, or raise PER_FILE_IGNORES_RULE_MAX here with a "
        "justification.\n"
        "Per-entry breakdown:\n  "
        + "\n  ".join(
            f"{k}: {len(v)} -> {v}" for k, v in sorted(table.items())
        )
    )
