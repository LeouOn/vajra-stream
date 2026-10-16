"""Provenance vocabulary: the honest instrument (docs/DEVELOPMENT_ROADMAP.md).

Every value the UI displays is exactly one of:

``record``
    A persisted fact: a sealed folio, a broadcast that started, a count of
    recitations, an operation's measured duration.
``computed``
    Deterministic from real inputs: planet longitude, moon phase, nakshatra,
    a rate derived from an intention's text.
``draw``
    Random, used as a divinatory method (the stick-pad analog, a tarot cast).
    Legitimate, but it reads as "drawn" and never as a measurement.
``decorative``
    Carries no information: animation, or a placeholder shown when the real
    calculation is unavailable.

The payload shape is shared across the codebase (core.operations,
core.radionics_engine, rng_attunement_service, RADIONICS_RATE_BROADCAST): a
``provenance`` key holding a map of *field name -> kind* for the derived values
beside it. A key names a top-level field of the same dict; a nested block (e.g.
``western``) is labeled as a whole. Image captions use the per-fact variant
``{"label", "value", "provenance"}`` from :func:`core.image_prompts.caption_fact`.

This module has no imports from the rest of the project, so any layer can use
it without growing an import cycle.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any, Literal

Provenance = Literal["record", "computed", "draw", "decorative"]

RECORD: Provenance = "record"
COMPUTED: Provenance = "computed"
DRAW: Provenance = "draw"
DECORATIVE: Provenance = "decorative"

PROVENANCE_KINDS: frozenset[str] = frozenset({RECORD, COMPUTED, DRAW, DECORATIVE})


def validate_provenance(mapping: Mapping[str, Any]) -> dict[str, str]:
    """Return ``mapping`` as a plain dict, raising ``ValueError`` on an unknown kind."""
    out: dict[str, str] = {}
    for key, kind in mapping.items():
        if kind not in PROVENANCE_KINDS:
            raise ValueError(f"provenance[{key!r}] must be one of {sorted(PROVENANCE_KINDS)}, got {kind!r}")
        out[str(key)] = str(kind)
    return out


def provenance_map(**fields: Provenance) -> dict[str, str]:
    """Build a validated ``{field: kind}`` map, e.g. ``provenance_map(moon_phase=COMPUTED)``."""
    return validate_provenance(fields)


def with_provenance(payload: MutableMapping[str, Any], mapping: Mapping[str, str]) -> MutableMapping[str, Any]:
    """Attach ``mapping`` as ``payload["provenance"]`` and return ``payload``.

    Labels the payload already carries win over ``mapping``: a producer that
    knows better (a hand-set dial, a fallback placeholder) keeps its label.
    Mutates and returns ``payload`` so it reads well at a ``return`` site.
    """
    merged = validate_provenance(mapping)
    existing = payload.get("provenance")
    if isinstance(existing, Mapping):
        merged.update(validate_provenance(existing))
    payload["provenance"] = merged
    return payload
