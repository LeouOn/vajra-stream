"""Losar-anchored Saka Dawa calendar — published dates, not Chinese month 4."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from core.tibetan_calendar import (
    saka_dawa_status,
    saka_dawa_window,
    tibetan_year_for,
)


@pytest.mark.unit
def test_2025_losar_is_a_month_after_chinese_new_year():
    """2025 is the divergence year: CNY Jan 29, Losar Feb 28.

    Chinese month 4 would put Duchen around mid-May. The real Duchen
    (FPMT) is June 11 — the full moon of the 4th month *after Losar*.
    """
    window = saka_dawa_window(2025)
    assert window is not None
    assert window.losar == date(2025, 2, 28)
    assert window.duchen == date(2025, 6, 11)
    assert window.month_start == date(2025, 5, 28)
    assert window.month_end == date(2025, 6, 25)


@pytest.mark.unit
def test_2026_matches_fpmt_and_tnp_published_window():
    window = saka_dawa_window(2026)
    assert window is not None
    assert window.losar == date(2026, 2, 18)
    assert window.duchen == date(2026, 5, 31)
    assert window.month_start == date(2026, 5, 17)
    assert window.month_end == date(2026, 6, 15)


@pytest.mark.unit
def test_2024_duchen_is_may_23():
    window = saka_dawa_window(2024)
    assert window is not None
    assert window.losar == date(2024, 2, 10)
    assert window.duchen == date(2024, 5, 23)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("when", "is_saka", "is_duchen", "multiplier"),
    [
        (date(2025, 6, 11), True, True, 100000),
        (date(2025, 6, 1), True, False, 10000),
        (date(2025, 4, 15), False, False, 1),  # after Losar, before month 4
        (date(2025, 1, 29), False, False, 1),  # Chinese NY — not Losar
        (date(2026, 5, 31), True, True, 100000),
        (date(2026, 8, 12), False, False, 1),
    ],
)
def test_status_for_known_civil_dates(when, is_saka, is_duchen, multiplier):
    status = saka_dawa_status(when)
    assert status["is_saka_dawa"] is is_saka
    assert status["is_duchen"] is is_duchen
    assert status["multiplier"] == multiplier
    assert status["calendar"] == "phugpa-losar"


@pytest.mark.unit
def test_january_belongs_to_previous_tibetan_year():
    assert tibetan_year_for(date(2026, 1, 15)) == 2025
    assert tibetan_year_for(date(2026, 2, 18)) == 2026


@pytest.mark.unit
def test_after_2026_saka_dawa_points_at_2027_duchen():
    status = saka_dawa_status(date(2026, 8, 12))
    assert status["is_saka_dawa"] is False
    assert status["saka_dawa_duchen"] == date(2027, 5, 21).isoformat()
    assert status["days_until_duchen"] == (date(2027, 5, 21) - date(2026, 8, 12)).days


@pytest.mark.unit
def test_datetime_input_preserves_isoformat_current_date():
    dt = datetime(2026, 5, 31, 8, 30, 0)
    status = saka_dawa_status(dt)
    assert status["is_duchen"] is True
    assert status["current_date"].startswith("2026-05-31T08:30:00")
