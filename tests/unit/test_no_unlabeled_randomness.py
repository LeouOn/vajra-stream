"""Guard: randomness in production Python needs a reviewed allow-list entry.

In the spirit of ``test_no_new_ruff_suppressions.py``. The honest-instrument
rule (docs/DEVELOPMENT_ROADMAP.md, Phase 2) says a random value must never
pose as a measurement. Draws are legitimate (the stick-pad analog), and
decorative randomness is fine, but each use must be a conscious decision.

This test parses every non-test ``.py`` file under ``backend/``, ``core/``
and ``modules/`` and finds uses of:

- the ``random`` module (``import random``, ``from random import ...``),
- NumPy's RNG (``np.random`` / ``numpy.random``),
- value-producing ``secrets`` calls (``randbelow``, ``choice``, ``randbits``).

``secrets.token_*`` (id generation) is deliberately not flagged.

Every file that uses randomness must appear in ``ALLOWED`` with a one-line
reason that says whether the randomness is a labeled **draw**, **decorative**,
or **content** selection (which text/variation to show, never a number shown
as a reading). Adding a file means review: if its random value is displayed or
reported to the LLM, it must carry ``provenance: "draw"``.

Stale entries fail too, so the list only ever describes real code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("backend", "core", "modules")

SECRETS_VALUE_FUNCS = {"randbelow", "choice", "randbits"}

# path (posix, relative to repo root) -> reason
ALLOWED: dict[str, str] = {
    # --- draws ---------------------------------------------------------------
    # Radionics draws carry provenance "draw" in every output. Divination casts
    # (a card, hexagram or figure) are draws by nature and never shown as a
    # measured number.
    "core/radionics_engine.py": "draw: GV, potency and dial draws (stick-pad analog); outputs carry provenance",
    "backend/core/services/rng_attunement_service.py": "draw: e-meter needle draws; readings carry provenance",
    "backend/core/services/true_rng_provider.py": "draw: entropy source behind the attunement draws (offline fallback)",
    "backend/core/services/divination_service.py": "draw: tarot / I Ching / geomancy casts, divination by nature",
    "backend/app/api/v1/endpoints/divination.py": "draw: geomancy mother figures, divination by nature",
    "core/ritual_generator.py": "draw: tarot, hexagram and geomancy picks for the ritual text",
    # --- content selection (which text or entity, not a reading) -----------
    "core/outlook_generator.py": "content: picks Buddha/yidam names and weighted realm/characters for the narrative",
    "core/blessing_narratives.py": "content: picks template phrases for blessing stories",
    "core/character_journey.py": "content: picks fallback template sentences",
    "core/character_generator.py": "content: fiction character name/stats for the journey story",
    "core/dharma_tales.py": "content: picks theme/tradition/archetype for a tale",
    "core/eighty_eight_buddhas.py": "content: picks which Buddha to contemplate",
    "core/prayer_wheel.py": "content: picks a traditional aspiration prayer",
    "modules/blessings.py": "content: picks a dedication text",
    "modules/radionics_operator.py": "content: picks style/tradition/tone words for an LLM blessing prompt",
    "backend/app/api/v1/endpoints/radionics.py": "content: picks one passage among equally-scored sutra passages",
    # --- decorative (texture, no information) ------------------------------
    "core/audio_generator.py": "decorative: intention-seeded modulation texture in the synthesized audio",
    "core/intelligent_composer.py": "decorative: intention-seeded modulation texture in the composition",
    "core/energetic_visualization.py": "decorative: color and pixel variation in generated images",
    "core/rothko_generator.py": "decorative: band layout and color variation in generated art",
}


def _iter_python_files():
    for top in SCAN_DIRS:
        for path in sorted((REPO_ROOT / top).rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            parts = rel.split("/")
            if "tests" in parts or "__pycache__" in parts or parts[-1].startswith("test_"):
                continue
            yield rel, path


def _attribute_chain(node: ast.AST) -> list[str]:
    names: list[str] = []
    while isinstance(node, ast.Attribute):
        names.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        names.append(node.id)
    return list(reversed(names))


def find_randomness(source: str) -> list[tuple[int, str]]:
    """Return ``(line, description)`` for each randomness use in ``source``."""
    tree = ast.parse(source)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random" or alias.name.startswith("numpy.random"):
                    hits.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "random" or mod.startswith("numpy.random"):
                hits.append((node.lineno, f"from {mod} import ..."))
            elif mod == "numpy" and any(a.name == "random" for a in node.names):
                hits.append((node.lineno, "from numpy import random"))
            elif mod == "secrets" and any(a.name in SECRETS_VALUE_FUNCS for a in node.names):
                hits.append((node.lineno, "from secrets import <value func>"))
        elif isinstance(node, ast.Attribute):
            chain = _attribute_chain(node)
            if len(chain) >= 2 and chain[0] in ("np", "numpy") and chain[1] == "random":
                hits.append((node.lineno, ".".join(chain[:3])))
            elif len(chain) == 2 and chain[0] == "secrets" and chain[1] in SECRETS_VALUE_FUNCS:
                hits.append((node.lineno, ".".join(chain)))
    return sorted(set(hits))


def _scan() -> dict[str, list[tuple[int, str]]]:
    found: dict[str, list[tuple[int, str]]] = {}
    for rel, path in _iter_python_files():
        hits = find_randomness(path.read_text(encoding="utf-8"))
        if hits:
            found[rel] = hits
    return found


@pytest.mark.unit
def test_no_unreviewed_randomness_in_production_python():
    found = _scan()
    unreviewed = {rel: hits for rel, hits in found.items() if rel not in ALLOWED}
    assert not unreviewed, (
        "Randomness found in files without an allow-list entry. If the value is shown in the UI or "
        "reported to the LLM, label it with provenance 'draw'; then add the file to ALLOWED in "
        f"{Path(__file__).name} with a one-line reason:\n"
        + "\n".join(f"  {rel}: {hits[:3]}" for rel, hits in sorted(unreviewed.items()))
    )


@pytest.mark.unit
def test_allow_list_has_no_stale_entries():
    found = _scan()
    stale = sorted(rel for rel in ALLOWED if rel not in found)
    assert not stale, f"Remove allow-list entries that no longer use randomness: {stale}"


@pytest.mark.unit
def test_every_allow_list_entry_names_its_kind():
    for rel, reason in ALLOWED.items():
        kind = reason.split(":", 1)[0]
        assert kind in {"draw", "content", "decorative"}, f"{rel}: reason must start with draw/content/decorative"
        assert len(reason.split(":", 1)[1].strip()) > 10, f"{rel}: reason must explain the use"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import random\nrandom.random()\n", True),
        ("import random as _r\n_r.choice([1])\n", True),
        ("from random import choice\n", True),
        ("import numpy as np\nnp.random.random()\n", True),
        ("from numpy import random\n", True),
        ("import secrets\nsecrets.randbelow(3)\n", True),
        ("import secrets\nsecrets.token_hex(4)\n", False),
        ("# random. in a comment\nx = 'random.choice'\n", False),
    ],
)
def test_detector(source, expected):
    assert bool(find_randomness(source)) is expected
