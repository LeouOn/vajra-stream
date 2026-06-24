"""Tests for ``core.compassionate_blessings`` — blessing target data + allocator.

Covers the public API:
- Enums: :class:`BlessingCategory`, :class:`MantraType`
- Dataclasses: :class:`GeoCoordinate`, :class:`BlessingCoordinate`,
  :class:`BlessingTarget` (including ``to_dict`` / ``from_dict`` round-trip
  and ``generate_identifier``)
- :class:`BlessingAllocator` — three static allocation strategies
- :func:`create_target` — convenience factory
- :class:`BlessingDatabase` — touched lightly with a temp file + a mocked
  ``init_db`` so the test never touches the global database.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from unittest.mock import patch

import pytest

from core.compassionate_blessings import (
    BlessingAllocator,
    BlessingCategory,
    BlessingCoordinate,
    BlessingDatabase,
    BlessingTarget,
    GeoCoordinate,
    MantraType,
    create_target,
)


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.compassionate_blessings as mod

    for name in (
        "BlessingCategory",
        "MantraType",
        "GeoCoordinate",
        "BlessingCoordinate",
        "BlessingTarget",
        "BlessingDatabase",
        "BlessingAllocator",
        "create_target",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Enum contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_blessing_category_enum_values():
    """BlessingCategory has the 12 documented categories."""
    expected = {
        "missing_person",
        "unidentified_remains",
        "shelter_animal",
        "refugee",
        "incarcerated",
        "homeless",
        "endangered_species",
        "hungry_ghost",
        "land_spirit",
        "deceased",
        "suffering_unknown",
        "all_sentient_beings",
    }
    assert {bc.value for bc in BlessingCategory} == expected


@pytest.mark.unit
def test_mantra_type_enum_values():
    """MantraType covers the 5 standard mantras + custom."""
    expected = {
        "om_mani_padme_hum",
        "bekandze",
        "om_tare_tuttare",
        "vajrasattva_100",
        "om_ami_dewa_hri",
        "custom",
    }
    assert {mt.value for mt in MantraType} == expected


# ---------------------------------------------------------------------------
# 3. BlessingTarget dataclass + identifier generation
# ---------------------------------------------------------------------------


def _make_target(**overrides) -> BlessingTarget:
    """Build a fully-populated BlessingTarget for serialization tests."""
    defaults = dict(
        identifier="",
        name="Test Being",
        category=BlessingCategory.SUFFERING_UNKNOWN,
        description="for tests",
        case_number="CASE-1",
        relevant_date=datetime(2024, 1, 1, 12, 0, 0),
        discovery_date=datetime(2024, 1, 2, 9, 0, 0),
        last_updated=datetime(2024, 1, 3, 8, 0, 0),
        photograph_path="/tmp/photo.jpg",
        additional_data={"source": "test"},
        mantras_dedicated=10,
        prayer_wheel_rotations=5,
        dedication_sessions=[datetime(2024, 1, 2, 9, 0, 0)],
        intention="Test intention",
        priority=7,
    )
    defaults.update(overrides)
    return BlessingTarget(**defaults)


@pytest.mark.unit
def test_blessing_target_generate_identifier_uses_explicit_value():
    """If identifier is set, generate_identifier returns it unchanged."""
    target = _make_target(identifier="EXPLICIT-123")
    assert target.generate_identifier() == "EXPLICIT-123"


@pytest.mark.unit
def test_blessing_target_generate_identifier_hashes_when_empty():
    """If identifier is empty, generate_identifier produces a stable hash."""
    t1 = _make_target(identifier="", name="Same Name", category=BlessingCategory.HUNGRY_GHOST)
    t2 = _make_target(identifier="", name="Same Name", category=BlessingCategory.HUNGRY_GHOST)
    assert t1.identifier == "" and t2.identifier == ""
    id1 = t1.generate_identifier()
    id2 = t2.generate_identifier()
    # Stable: same inputs => same output
    assert id1 == id2
    # Well-formed: starts with category prefix
    assert id1.startswith("hungry_ghost_")
    # 12 hex chars after the prefix
    assert len(id1.split("_")[-1]) == 12


# ---------------------------------------------------------------------------
# 4. BlessingTarget to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_blessing_target_to_dict_has_all_expected_fields():
    """to_dict serialises every dataclass field into a plain dict."""
    target = _make_target(
        coordinates=BlessingCoordinate(
            julian_day=2460000.5,
            calendar_system="gregorian",
            location=GeoCoordinate(latitude=10.0, longitude=20.0, location_name="Test Loc"),
        )
    )
    d = target.to_dict()

    assert d["identifier"] == ""
    assert d["name"] == "Test Being"
    assert d["category"] == "suffering_unknown"
    assert d["description"] == "for tests"
    assert d["case_number"] == "CASE-1"
    assert d["relevant_date"] == "2024-01-01T12:00:00"
    assert d["discovery_date"] == "2024-01-02T09:00:00"
    assert d["last_updated"] == "2024-01-03T08:00:00"
    assert d["mantras_dedicated"] == 10
    assert d["prayer_wheel_rotations"] == 5
    assert d["dedication_sessions"] == ["2024-01-02T09:00:00"]
    assert d["intention"] == "Test intention"
    assert d["priority"] == 7
    # Nested coordinate round-trip
    assert d["coordinates"]["julian_day"] == 2460000.5
    assert d["coordinates"]["location"]["latitude"] == 10.0
    assert d["coordinates"]["location"]["location_name"] == "Test Loc"


@pytest.mark.unit
def test_blessing_target_from_dict_round_trip_preserves_data():
    """to_dict -> from_dict yields an equivalent BlessingTarget."""
    original = _make_target(
        identifier="RT-001",
        coordinates=BlessingCoordinate(
            julian_day=2460123.5,
            location=GeoCoordinate(latitude=-33.8688, longitude=151.2093, location_name="Sydney"),
        ),
    )
    d = original.to_dict()
    restored = BlessingTarget.from_dict(d)

    # Identifier, name, category, dates, counts all survive
    assert restored.identifier == original.identifier
    assert restored.name == original.name
    assert restored.category == original.category
    assert restored.relevant_date == original.relevant_date
    assert restored.discovery_date == original.discovery_date
    assert restored.last_updated == original.last_updated
    assert restored.mantras_dedicated == original.mantras_dedicated
    assert restored.prayer_wheel_rotations == original.prayer_wheel_rotations
    assert restored.dedication_sessions == original.dedication_sessions
    assert restored.intention == original.intention
    assert restored.priority == original.priority
    # Nested coordinate
    assert restored.coordinates is not None
    assert restored.coordinates.julian_day == 2460123.5
    assert restored.coordinates.location is not None
    assert restored.coordinates.location.latitude == -33.8688
    assert restored.coordinates.location.location_name == "Sydney"


@pytest.mark.unit
def test_blessing_target_from_dict_handles_missing_optional_fields():
    """from_dict accepts a dict with only the required 'identifier' key."""
    minimal = {"identifier": "MIN-1"}
    target = BlessingTarget.from_dict(minimal)
    assert target.identifier == "MIN-1"
    assert target.name is None
    assert target.category == BlessingCategory.SUFFERING_UNKNOWN
    assert target.relevant_date is None
    assert target.discovery_date is None
    assert target.dedication_sessions == []
    assert target.coordinates is None


# ---------------------------------------------------------------------------
# 5. BlessingAllocator — three strategies
# ---------------------------------------------------------------------------


def _targets_with_priorities(priorities: list[int]) -> list[BlessingTarget]:
    return [
        BlessingTarget(identifier=f"T{i}", name=f"Target {i}", priority=p)
        for i, p in enumerate(priorities)
    ]


@pytest.mark.unit
def test_allocator_equitable_distributes_evenly_with_remainder():
    """Equitable: 100 mantras across 3 targets => 34/33/33 (remainder 1 goes to first)."""
    targets = _targets_with_priorities([5, 5, 5])
    result = BlessingAllocator.allocate_equitable(100, targets)

    assert sum(result.values()) == 100
    # Each target gets at least floor(100/3) = 33
    for v in result.values():
        assert v == 33 or v == 34
    # Identifiers match target identifiers
    assert set(result.keys()) == {"T0", "T1", "T2"}


@pytest.mark.unit
def test_allocator_equitable_handles_empty_target_list():
    """Equitable: empty target list returns an empty allocation."""
    assert BlessingAllocator.allocate_equitable(100, []) == {}


@pytest.mark.unit
def test_allocator_urgent_favours_high_priority_old_targets():
    """Urgent: combination of days_waiting × priority drives the share.

    Higher-priority and older targets should get more mantras than the
    low-priority, brand-new target. The contract: total mantras preserved.
    """
    old_high = datetime(2020, 1, 1, 12, 0, 0)
    recent_low = datetime(2026, 1, 1, 12, 0, 0)
    t1 = BlessingTarget(identifier="A", relevant_date=old_high, priority=10)
    t2 = BlessingTarget(identifier="B", relevant_date=recent_low, priority=1)
    targets = [t1, t2]

    result = BlessingAllocator.allocate_urgent(1000, targets)
    assert sum(result.values()) == 1000
    assert result["A"] > result["B"], "Older high-priority target should get more"


@pytest.mark.unit
def test_allocator_weighted_proportional_to_priority():
    """Weighted: mantras split proportionally to priority, total preserved."""
    targets = _targets_with_priorities([1, 3, 6])  # total priority = 10
    result = BlessingAllocator.allocate_weighted(100, targets)

    assert sum(result.values()) == 100
    # Ratio: T0 : T1 : T2 = 1 : 3 : 6 => ~10 : ~30 : ~60
    assert result["T0"] < result["T1"] < result["T2"]
    assert result["T2"] > result["T0"]


@pytest.mark.unit
def test_allocator_weighted_handles_zero_priorities():
    """Weighted: all-zero priorities => equal split (avoids div-by-zero)."""
    targets = _targets_with_priorities([0, 0, 0])
    result = BlessingAllocator.allocate_weighted(90, targets)
    assert sum(result.values()) == 90
    # Each gets 30
    for v in result.values():
        assert v == 30


# ---------------------------------------------------------------------------
# 6. create_target factory
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_target_with_no_location_or_date():
    """create_target without location/date builds a valid BlessingTarget with
    no coordinates (and no exception)."""
    target = create_target(
        name="Anonymous",
        category=BlessingCategory.ALL_SENTIENT_BEINGS,
        priority=10,
    )
    assert isinstance(target, BlessingTarget)
    assert target.name == "Anonymous"
    assert target.category == BlessingCategory.ALL_SENTIENT_BEINGS
    assert target.priority == 10
    # Without location or date, coordinates should be None
    assert target.coordinates is None
    # Identifier is left empty (will be generated lazily)
    assert target.identifier == ""


@pytest.mark.unit
def test_create_target_with_location_and_date_attaches_coordinates():
    """create_target with location + date builds a BlessingCoordinate
    containing a GeoCoordinate and a Julian day."""
    target = create_target(
        name="Located",
        category=BlessingCategory.MISSING_PERSON,
        location=(40.7128, -74.0060),  # NYC
        date=datetime(2020, 6, 15, 14, 30, 0),
        description="Missing since June 2020",
        priority=8,
    )
    assert target.coordinates is not None
    assert target.coordinates.location is not None
    assert target.coordinates.location.latitude == 40.7128
    assert target.coordinates.location.longitude == -74.0060
    # Julian day is a positive float
    assert isinstance(target.coordinates.julian_day, float)
    assert target.coordinates.julian_day > 0


# ---------------------------------------------------------------------------
# 7. BlessingDatabase — contract test with mocked sqlite3
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Minimal stand-in for a sqlite3 cursor with controlled fetchone/all."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._calls = []
        self.executed: list[tuple] = []
        self.lastrowid = 0

    def execute(self, sql, params=()):
        self.executed.append((sql.strip().split()[0].upper(), params))
        return self

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def close(self):
        pass


class _FakeConnection:
    """Captures SQL calls and returns scripted rows."""

    def __init__(self, rows=None):
        self.cursor_obj = _FakeCursor(rows=rows)
        self.commits = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_blessing_database_add_and_get_target_round_trip():
    """Add a target then read it back: data survives the round trip.

    We mock ``core.schema.init_db`` AND ``sqlite3.connect`` so the test
    does not touch any real database file. The contract is verified by
    inspecting the SQL operations and the reconstructed dataclass.
    """
    # Pre-script the SELECT for get_target to return a row matching what
    # add_target would have inserted (the test's _make_target shape).
    from datetime import datetime as _dt

    script_row = (
        "DB-1",                # identifier
        "DB Being",            # name
        "suffering_unknown",   # category
        "for tests",           # description
        "CASE-1",              # case_number
        _dt(2024, 1, 1, 12, 0, 0).isoformat(),  # relevant_date
        _dt(2024, 1, 2, 9, 0, 0).isoformat(),   # discovery_date
        _dt(2024, 1, 3, 8, 0, 0).isoformat(),   # last_updated
        None,                  # coordinates_json
        "/tmp/photo.jpg",      # photograph_path
        '{"source": "test"}',  # additional_data_json
        10,                    # mantras_dedicated
        5,                     # prayer_wheel_rotations
        '[]',                  # dedication_sessions_json
        "Test intention",      # intention
        4,                     # priority
    )

    fake_conn = _FakeConnection(rows=[script_row])

    with patch("core.schema.init_db") as mock_init, patch(
        "core.compassionate_blessings.sqlite3.connect", return_value=fake_conn
    ):
        db = BlessingDatabase(db_path="ignored.db")
        mock_init.assert_called_once()  # schema bootstrap is invoked

        target = _make_target(identifier="DB-1", name="DB Being", priority=4)
        db.add_target(target)

        # add_target issues an INSERT
        assert fake_conn.cursor_obj.executed[0][0] == "INSERT"
        # values match the target fields
        params = fake_conn.cursor_obj.executed[0][1]
        assert params[0] == "DB-1"
        assert params[1] == "DB Being"

        loaded = db.get_target("DB-1")

    assert loaded is not None
    assert loaded.identifier == "DB-1"
    assert loaded.name == "DB Being"
    assert loaded.priority == 4
    assert loaded.category == BlessingCategory.SUFFERING_UNKNOWN
    assert loaded.mantras_dedicated == 10


@pytest.mark.unit
def test_blessing_database_get_target_returns_none_for_missing_id():
    """get_target returns None (not raises) for an unknown identifier."""
    fake_conn = _FakeConnection(rows=[])  # fetchone() => None

    with patch("core.schema.init_db"), patch(
        "core.compassionate_blessings.sqlite3.connect", return_value=fake_conn
    ):
        db = BlessingDatabase(db_path="ignored.db")
        assert db.get_target("DOES-NOT-EXIST") is None
    # Connection is closed after the call
    assert fake_conn.closed is True


# ---------------------------------------------------------------------------
# 8. Error handling: invalid enum value in from_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_blessing_target_from_dict_raises_on_invalid_category():
    """from_dict with an unknown category string raises ValueError.

    This guards against silent corruption if the on-disk format ever drifts
    from the enum.
    """
    bad = {"identifier": "X", "category": "not_a_real_category"}
    with pytest.raises(ValueError):
        BlessingTarget.from_dict(bad)
