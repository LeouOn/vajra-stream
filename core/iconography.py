"""Curated deity iconography: lookup, image-prompt clauses and caption facts.

Image models given only a name ("Avalokiteshvara") paint a generic or wrong
figure. ``knowledge/iconography.json`` records, per deity and per form, the
well-established attributes from standard references (body colour, faces and
arms, posture and seat, the gesture and object of each hand, ornaments, halo)
and nothing more: a field the references do not settle is ``null`` and is
simply left out of the prompt. This module turns an entry into

* :func:`deity_prompt_clause` -- a concise visual description for an image
  model (the caller still passes the whole prompt through
  :func:`core.image_prompts.finalize_image_prompt`, so the no-text rule holds);
* :func:`deity_caption_facts` -- ``record`` caption facts naming the deity and
  the sources its iconography comes from.

Pure: reads one JSON file, imports nothing above ``core``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.image_prompts import caption_fact

ICONOGRAPHY_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "iconography.json"

#: Prompt budget when a deity clause leads it: the clause alone runs to about a
#: thousand characters, and the intention, sky and suffix must still fit after it.
DEITY_PROMPT_MAX_CHARS = 2200

# Deities never inferred from free text (Outlook narratives): the generic Buddha
# form ("88 Buddhas" is a liturgy, not a figure to paint) and Prajnaparamita,
# whose name usually means the sutra rather than the goddess.
_TEXT_MATCH_EXCLUDED = frozenset({"buddha_generic", "prajnaparamita"})

_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    6: "six",
    7: "seven",
    8: "eight",
    11: "eleven",
    18: "eighteen",
    1000: "a thousand",
}

# Hands described one by one; any other label (ordinal or repeated) is grouped by side.
_HAND_PHRASES = {
    "right": "the right hand",
    "left": "the left hand",
    "both": "both hands",
    "principal pair": "the principal pair of hands",
    "upper right": "the upper right hand",
    "upper left": "the upper left hand",
}


# -- data --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_iconography() -> dict[str, Any]:
    """The whole curated dataset (cached; treat it as read-only)."""
    data: dict[str, Any] = json.loads(ICONOGRAPHY_PATH.read_text(encoding="utf-8"))
    return data


def deities() -> list[dict[str, Any]]:
    return list(load_iconography()["deities"])


def buddha_families() -> dict[str, dict[str, Any]]:
    """The five Buddha families keyed by id (``tathagata``, ``vajra``, ``ratna``, ``padma``, ``karma``)."""
    families: dict[str, dict[str, Any]] = load_iconography()["buddha_families"]["families"]
    return families


def get_deity(deity_id: str) -> dict[str, Any] | None:
    for entry in deities():
        if entry["id"] == deity_id:
            return entry
    return None


def get_form(entry: dict[str, Any], form: str | dict[str, Any] | None = None) -> dict[str, Any]:
    """The named form of ``entry`` (a form dict passes through); the default form otherwise."""
    if isinstance(form, dict):
        return form
    wanted = form or entry["default_form"]
    forms: list[dict[str, Any]] = entry["forms"]
    for candidate in forms:
        if candidate["id"] == wanted:
            return candidate
    raise KeyError(f"deity {entry['id']!r} has no form {wanted!r}")


def source_citations(entry: dict[str, Any], *, short: bool = False) -> list[str]:
    registry = load_iconography()["sources"]
    key = "short" if short else "citation"
    return [registry[source_id][key] for source_id in entry.get("sources") or []]


# -- lookup ------------------------------------------------------------------------


@dataclass(frozen=True)
class DeityRef:
    """A resolved deity and form."""

    entry: dict[str, Any]
    form: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.entry["id"])

    @property
    def form_id(self) -> str:
        return str(self.form["id"])

    @property
    def label(self) -> str:
        return str(self.form.get("label") or self.entry["names"]["english"])

    def record(self) -> dict[str, str]:
        """What a folio stores: ``{"id", "form", "label"}``."""
        return {"id": self.id, "form": self.form_id, "label": self.label}


def normalize_name(text: str) -> str:
    """Lowercase, diacritics folded, punctuation and underscores to single spaces (CJK kept)."""
    folded = unicodedata.normalize("NFKD", str(text))
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch)).lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in folded).split())


def _entry_names(entry: dict[str, Any]) -> list[str]:
    names = entry.get("names") or {}
    return [entry["id"], *(entry.get("practice_ids") or []), names.get("english") or "", names.get("sanskrit") or ""]


@lru_cache(maxsize=1)
def _alias_index() -> tuple[dict[str, tuple[str, str | None]], tuple[tuple[str, tuple[str, str | None]], ...]]:
    """``(index, conflicts)``: normalized alias -> (deity id, form id or None for the default)."""
    index: dict[str, tuple[str, str | None]] = {}
    conflicts: list[tuple[str, tuple[str, str | None]]] = []

    def add(alias: str, target: tuple[str, str | None]) -> None:
        key = normalize_name(alias)
        if not key:
            return
        existing = index.get(key)
        if existing is None:
            index[key] = target
        elif existing != target and existing[0] != target[0]:
            conflicts.append((key, target))

    for entry in deities():
        for form in entry["forms"]:
            if form["id"] != entry["default_form"]:
                for alias in form.get("aliases") or []:
                    add(alias, (entry["id"], form["id"]))
                add(f"{entry['id']} {form['id']}", (entry["id"], form["id"]))
            else:
                for alias in form.get("aliases") or []:
                    add(alias, (entry["id"], None))
        for alias in [*_entry_names(entry), *(entry.get("aliases") or [])]:
            add(alias, (entry["id"], None))
    return index, tuple(conflicts)


def alias_conflicts() -> list[tuple[str, tuple[str, str | None]]]:
    """Aliases claimed by two different deities (the data tests require none)."""
    return list(_alias_index()[1])


def _candidates(name: str) -> list[str]:
    """``name`` itself, then its text outside brackets, then each bracketed or ``/``-separated part."""
    text = str(name).strip()
    out = [text]
    outside = re.sub(r"[(\[][^)\]]*[)\]]", " ", text)
    out.append(outside)
    pieces = re.findall(r"[(\[]([^)\]]*)[)\]]", text)
    for chunk in (outside, *pieces):
        out.extend(re.split(r"\s*(?:/|,|;|\bor\b|\baka\b)\s*", chunk))
    return [c for c in out if c.strip()]


def resolve(name: str | None, form: str | None = None) -> DeityRef | None:
    """Resolve an id, alias or display string to a deity and form, or ``None``.

    Accepts ids (``green_tara``), practice ids (``zhunti``, ``88_buddhas``),
    the population ``deity`` strings ("Avalokiteshvara (Chenrezig)",
    "Zhunti (Cundi) Buddha Mother"), form aliases ("thousand-armed Chenrezig")
    and ``"<id>:<form>"``. An explicit ``form`` overrides; an unknown form is
    an error rather than a silent fallback.
    """
    if not name or not str(name).strip():
        return None
    text = str(name).strip()
    if ":" in text and form is None:
        head, _, tail = text.partition(":")
        if get_deity(head.strip()) is not None:
            text, form = head.strip(), tail.strip() or None
    index, _ = _alias_index()
    for candidate in _candidates(text):
        hit = index.get(normalize_name(candidate))
        if hit is None:
            continue
        entry = get_deity(hit[0])
        if entry is None:
            continue
        try:
            return DeityRef(entry, get_form(entry, form or hit[1]))
        except KeyError:
            return None  # a known deity with an unknown form is not silently the default form
    return None


def lookup(name: str | None) -> dict[str, Any] | None:
    """The deity entry for an id, alias or display string, or ``None``."""
    ref = resolve(name)
    return None if ref is None else ref.entry


def named_deity_in_text(text: str | None) -> DeityRef | None:
    """The one deity a free text names by an unambiguous alias, else ``None``.

    Conservative by design (for Outlook illustrations): the generic Buddha form
    and Prajnaparamita are never inferred, and a text naming two or more
    different deities yields ``None``.
    """
    if not text:
        return None
    haystack = f" {normalize_name(text)} "
    index, _ = _alias_index()
    found: dict[str, set[str | None]] = {}
    for alias, (deity_id, form_id) in index.items():
        if deity_id in _TEXT_MATCH_EXCLUDED or (len(alias) < 4 and alias.isascii()):
            continue
        needle = f" {alias} " if alias.isascii() else alias
        if needle in haystack:
            found.setdefault(deity_id, set()).add(form_id)
    if len(found) != 1:
        return None
    deity_id, forms = next(iter(found.items()))
    entry = get_deity(deity_id)
    if entry is None:
        return None
    named_forms = {f for f in forms if f is not None}
    return DeityRef(entry, get_form(entry, next(iter(named_forms)) if len(named_forms) == 1 else None))


def folio_deity(folio: dict[str, Any]) -> DeityRef | None:
    """The deity a sealed folio names (``folio["deity"]``: a ``{"id", "form"}`` record or a string)."""
    raw = folio.get("deity")
    if isinstance(raw, dict):
        entry = get_deity(str(raw.get("id") or ""))
        if entry is None:
            return None
        try:
            return DeityRef(entry, get_form(entry, raw.get("form")))
        except KeyError:
            return DeityRef(entry, get_form(entry))
    if isinstance(raw, str):
        try:
            return resolve(raw)
        except KeyError:
            return None
    return None


def list_deities() -> list[dict[str, Any]]:
    """A summary per deity (for pickers): id, names, forms, default form, generic flag, Buddha family."""
    return [
        {
            "id": entry["id"],
            "name": entry["names"]["english"],
            "names": entry["names"],
            "generic": bool(entry.get("generic")),
            "buddha_family": entry.get("buddha_family"),
            "default_form": entry["default_form"],
            "forms": [{"id": form["id"], "label": form["label"]} for form in entry["forms"]],
            "sources": source_citations(entry),
        }
        for entry in deities()
    ]


# -- prompt clause -----------------------------------------------------------------


def _count(n: int | None, noun: str) -> str | None:
    if n is None:
        return None
    word = _NUMBER_WORDS.get(int(n))
    if word is None:
        return None
    plural = noun if int(n) == 1 else f"{noun}s"
    return f"{word} {plural}"


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _hand_text(hand: dict[str, Any]) -> str | None:
    head = " ".join(b for b in (_HAND_PHRASES[hand["hand"]], hand.get("position")) if b)
    bits = []
    if hand.get("mudra"):
        bits.append(f"in {hand['mudra']}")
    if hand.get("holds"):
        bits.append(f"holding {hand['holds']}")
    if not bits and not hand.get("position"):
        return None
    return ", ".join([head, *bits])


def _grouped_hands(hands: list[dict[str, Any]], side: str) -> str | None:
    gestures = [h["mudra"] for h in hands if h.get("mudra")]
    holds = [h["holds"] for h in hands if h.get("holds")]
    verbs = []
    if gestures:
        verbs.append(f"make {_join(gestures)}")
    if holds:
        verbs.append(f"hold {_join(holds)}")
    if not verbs:
        return None
    return f"the other {side} hands {' and '.join(verbs)}"


def _hands_clause(form: dict[str, Any]) -> list[str]:
    hands = list(form.get("hands") or [])
    labels = [h["hand"] for h in hands]
    single = [h for h in hands if h["hand"] in _HAND_PHRASES and labels.count(h["hand"]) == 1]
    grouped = [h for h in hands if h not in single]
    out = [text for text in (_hand_text(h) for h in single) if text]
    for side in ("right", "left"):
        side_hands = [h for h in grouped if str(h["hand"]).startswith(side)]
        text = _grouped_hands(side_hands, side)
        if text:
            out.append(text)
    if form.get("other_hands"):
        out.append(str(form["other_hands"]))
    return out


def deity_prompt_clause(entry: dict[str, Any], form: str | dict[str, Any] | None = None) -> str:
    """A concise, reverent visual description of the deity for an image model.

    Built only from the curated fields; ``null`` fields are left out. Contains
    no digits, script or mantra text, and asks for none to be painted.
    """
    data = load_iconography()
    chosen = get_form(entry, form)
    style = data["art_styles"].get(entry.get("art_style") or "", data["art_styles"]["tibetan_thangka"])

    figure = str(chosen.get("descriptor") or "a deity")
    if chosen.get("body_colour"):
        figure += f" with a {chosen['body_colour']} body"
    counts = [c for c in (_count(chosen.get("faces"), "face"), _count(chosen.get("arms"), "arm")) if c]
    if counts:
        figure += f", {_join(counts)}"
    if chosen.get("features"):
        figure += f", {chosen['features']}"

    clauses = [figure]
    seat = chosen.get("seat")
    posture = ", ".join(str(p) for p in (seat and f"upon {seat}", chosen.get("posture")) if p)
    if posture:
        clauses.append(posture)
    clauses.extend(_hands_clause(chosen))
    ornament = data["ornament_sets"].get(chosen.get("ornaments") or "")
    if ornament:
        verb = "wearing" if chosen.get("ornaments") == "nirmanakaya" else "adorned with"
        clauses.append(f"{verb} {ornament}")
    if chosen.get("halo"):
        clauses.append(str(chosen["halo"]))

    label = str(chosen.get("label") or entry["names"]["english"])
    return (
        f"{style} of {label}: {'; '.join(clauses)}. "
        "Reverent and iconographically faithful, mineral pigments and fine gold line; "
        "no seed syllables or mantra script."
    )


def ref_prompt_clause(ref: DeityRef) -> str:
    return deity_prompt_clause(ref.entry, ref.form)


# -- caption facts -----------------------------------------------------------------


def _names_value(entry: dict[str, Any], form: dict[str, Any]) -> str:
    names = entry["names"]
    head = str(form.get("label") or names["english"])
    others = [str(names[k]) for k in ("sanskrit", "tibetan", "chinese") if names.get(k)]
    others = [o for o in others if normalize_name(o) != normalize_name(head)]
    return f"{head} ({'; '.join(others)})" if others else head


def _clip(text: str, limit: int = 300) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip(" ,;") + "…"


def deity_caption_facts(entry: dict[str, Any], form: str | dict[str, Any] | None = None) -> list[dict[str, str]]:
    """``record`` caption facts: the deity's names and where its iconography comes from."""
    chosen = get_form(entry, form)
    facts = [caption_fact("Deity", _clip(_names_value(entry, chosen)), "record")]
    if entry.get("generic"):
        facts.append(
            caption_fact(
                "Iconography",
                "generic Buddha form: these Buddhas have no individually established iconography",
                "record",
            )
        )
    sources = "; ".join(source_citations(entry, short=True))
    facts.append(caption_fact("Iconography source", _clip(f"curated record after {sources}"), "record"))
    return facts
