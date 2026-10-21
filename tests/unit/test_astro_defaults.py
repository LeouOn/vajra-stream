"""W1-7: one default location, reported rather than hidden.

The learner confirmed (2026-10-08) that a missing location may default to San
Francisco. Before this module existed that default was applied inconsistently
and silently: some call sites used San Francisco and some fell back to
``(0.0, 0.0)`` in the Gulf of Guinea without saying so.

These tests pin the contract of ``core.astro.defaults``: a resolved location
always says where it came from, and an invalid coordinate is refused with a
message that names the field rather than being clamped or ignored.
"""

from __future__ import annotations

import math
import pathlib

import pytest

from core.astro import defaults


def test_default_location_is_san_francisco() -> None:
    """The constant is exactly the two literals the learner confirmed."""
    assert defaults.DEFAULT_LOCATION == (37.7749, -122.4194)
    lat, lon = defaults.DEFAULT_LOCATION
    assert lat == 37.7749
    assert lon == -122.4194


def test_default_location_is_named_in_the_docstring() -> None:
    """The default must be discoverable, not just a bare tuple."""
    doc = defaults.__doc__ or ""
    assert "San Francisco" in doc
    assert "37.7749" in doc and "-122.4194" in doc


def test_given_location_passes_through_as_given() -> None:
    """Values the caller supplied are used unchanged and are not 'defaulted'."""
    resolved = defaults.resolve_location((10.5, -20.25))
    assert resolved.lat == 10.5
    assert resolved.lon == -20.25
    assert resolved.source == "given"
    assert resolved.warnings == ()


def test_given_lat_lon_pass_through_as_given() -> None:
    """The keyword form is equivalent to the tuple form."""
    resolved = defaults.resolve_location(None, lat=1.5, lon=2.5)
    assert (resolved.lat, resolved.lon) == (1.5, 2.5)
    assert resolved.source == "given"
    assert resolved.warnings == ()


def test_missing_location_uses_the_default_and_says_so() -> None:
    """No location at all: the default is used AND it is reported."""
    resolved = defaults.resolve_location(None)
    assert (resolved.lat, resolved.lon) == defaults.DEFAULT_LOCATION
    assert resolved.source == "default_sf"
    assert len(resolved.warnings) == 1
    warning = resolved.warnings[0]
    assert "default" in warning.lower()
    assert "San Francisco" in warning


def test_latitude_out_of_range_is_refused() -> None:
    """An out-of-range latitude is an error, never silently clamped."""
    for bad in (90.1, 91.0, -90.1, -91.0, 1000.0):
        with pytest.raises(ValueError) as excinfo:
            defaults.resolve_location(None, lat=bad, lon=0.0)
        message = str(excinfo.value)
        assert "lat" in message.lower(), message


def test_longitude_out_of_range_is_refused() -> None:
    """An out-of-range longitude is an error, never silently clamped."""
    for bad in (180.1, 181.0, -180.1, -181.0, 1000.0):
        with pytest.raises(ValueError) as excinfo:
            defaults.resolve_location(None, lat=0.0, lon=bad)
        message = str(excinfo.value)
        assert "lon" in message.lower(), message


def test_boundary_values_are_accepted() -> None:
    """The extremes are inside the range, so they are legal."""
    for lat, lon in ((90.0, 180.0), (-90.0, -180.0), (0.0, 0.0)):
        resolved = defaults.resolve_location((lat, lon))
        assert (resolved.lat, resolved.lon) == (lat, lon)
        assert resolved.source == "given"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_are_refused(bad: float) -> None:
    """NaN and infinity are not coordinates."""
    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=bad, lon=0.0)
    assert "lat" in str(excinfo.value).lower()

    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=0.0, lon=bad)
    assert "lon" in str(excinfo.value).lower()


def test_a_string_that_looks_numeric_is_refused() -> None:
    """'37.7749' is not a coordinate; it must not be silently coerced."""
    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat="37.7749", lon=0.0)  # type: ignore[arg-type]
    assert "lat" in str(excinfo.value).lower()

    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=0.0, lon="-122.4194")  # type: ignore[arg-type]
    assert "lon" in str(excinfo.value).lower()


def test_a_boolean_is_refused() -> None:
    """True is an int in Python, but it is not a coordinate."""
    with pytest.raises(ValueError):
        defaults.resolve_location(None, lat=True, lon=0.0)  # type: ignore[arg-type]


def test_only_one_of_lat_lon_is_refused() -> None:
    """Half a location is a mistake, not a request for the default."""
    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=10.0)
    assert "lon" in str(excinfo.value).lower()

    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lon=10.0)
    assert "lat" in str(excinfo.value).lower()


def test_a_malformed_location_tuple_is_refused() -> None:
    """A tuple of the wrong shape is an error, not a silent default."""
    with pytest.raises(ValueError):
        defaults.resolve_location((10.0,))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        defaults.resolve_location((10.0, 20.0, 30.0))  # type: ignore[arg-type]


def test_resolved_location_is_frozen() -> None:
    """A resolved location is a value, not something to mutate later."""
    resolved = defaults.resolve_location((1.0, 2.0))
    with pytest.raises(Exception):
        resolved.lat = 5.0  # type: ignore[misc]


def test_the_module_is_pure_and_has_no_project_imports() -> None:
    """A pure module: no database, no core.astrology internals, no side effects.

    Checked on the IMPORT statements (not the whole file, so the prose that
    explains what the module does not count as a dependency).
    """
    import ast

    source = pathlib.Path(defaults.__file__).read_text()
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(name.startswith("core.") for name in imported), imported
    assert not any(name.startswith("backend.") for name in imported), imported
    assert "sqlite" not in imported, imported
    assert "core.astrology" not in source.replace("``core.astrology``", "")


def test_the_default_is_not_the_gulf_of_guinea() -> None:
    """The whole point: the default is San Francisco, not (0.0, 0.0)."""
    lat, lon = defaults.DEFAULT_LOCATION
    assert not (lat == 0.0 and lon == 0.0)
    assert math.isfinite(lat) and math.isfinite(lon)


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"lat": 10**400, "lon": 0.0}, "lat"),
        ({"lat": 0.0, "lon": 10**400}, "lon"),
        ({"lat": -(10**400), "lon": 0.0}, "lat"),
        ({"lat": 0.0, "lon": -(10**400)}, "lon"),
    ],
)
def test_huge_integer_coordinates_raise_value_error(kwargs: dict, field: str) -> None:
    """A coordinate too large to convert to a float is still just invalid.

    float() raises OverflowError for a huge int, which is not the documented
    exception: every invalid coordinate must raise ValueError naming the field.
    """
    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, **kwargs)  # type: ignore[arg-type]
    message = str(excinfo.value)
    assert field in message.lower(), message
    assert "finite" in message.lower() or "must be" in message.lower(), message


def test_a_huge_integer_does_not_produce_a_huge_message() -> None:
    """A 4,000-digit integer must not turn into a 4,000-character message."""
    huge = 10**4000
    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=huge, lon=0.0)  # type: ignore[arg-type]
    message = str(excinfo.value)
    assert len(message) < 120, f"the message is {len(message)} characters long"
    assert "lat" in message.lower()
    assert "..." in message, "the truncated value should be marked as truncated"

    with pytest.raises(ValueError) as excinfo:
        defaults.resolve_location(None, lat=0.0, lon=huge)  # type: ignore[arg-type]
    assert len(str(excinfo.value)) < 120
    assert "lon" in str(excinfo.value).lower()
