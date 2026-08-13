"""Phugpa / CTA Tibetan calendar helpers for Saka Dawa.

Saka Dawa is the 4th month of the Tibetan lunar year that begins at Losar
(Tibetan New Year, day 1 of month 1). Saka Dawa Duchen is the 15th day of
that month — the full moon that commemorates the Buddha's birth,
enlightenment, and parinirvana.

The Chinese lunisolar calendar (lunar-python) is *not* a substitute. In
years when Losar falls a month after Chinese New Year (2022, 2025, 2030,
2033) Chinese month 4 is the wrong month.

This module:

1. Uses published Phugpa/CTA Losar dates as month-1 day-1.
2. Counts three mean synodic months forward to reach month 4.
3. Prefers FPMT/TNP published Duchen dates when they exist.

Leap months that fall *between* Losar and month 4 are rare. When a
published Duchen disagrees with the 3-month count by more than 3 days,
the window is shifted to the published full moon (that is the leap-month
case). Years without a Losar entry fall back to the Chinese month-4
proxy and are marked ``calendar="chinese_proxy"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

# Mean synodic month. Counting from a published Losar (itself a new-moon
# civil date) lands on the published 2024–2026 Saka Dawa windows to the day.
SYNODIC_DAYS = 29.530588

# Phugpa / CTA Losar (1st day of the 1st Tibetan month).
# 2022–2026: Tibetan Nuns Project / FPMT / CTA announcements.
# 2027–2036: qppstudio compiled observances (same civil dates as CTA).
LOSAR_DATES: dict[int, date] = {
    2022: date(2022, 3, 3),
    2023: date(2023, 2, 21),
    2024: date(2024, 2, 10),
    2025: date(2025, 2, 28),
    2026: date(2026, 2, 18),
    2027: date(2027, 2, 7),
    2028: date(2028, 2, 26),
    2029: date(2029, 2, 14),
    2030: date(2030, 3, 5),
    2031: date(2031, 2, 22),
    2032: date(2032, 2, 12),
    2033: date(2033, 3, 2),
    2034: date(2034, 2, 19),
    2035: date(2035, 2, 9),
    2036: date(2036, 2, 27),
}

# FPMT-published Saka Dawa Duchen (15th of the 4th Tibetan month).
DUCHEN_DATES: dict[int, date] = {
    2024: date(2024, 5, 23),
    2025: date(2025, 6, 11),
    2026: date(2026, 5, 31),
}

# Extra lunar months between Losar and Saka Dawa. Default 0.
# Add an entry only when a published Duchen is ~one month later than the
# 3-synodic-month count and we have confirmed a leap month.
LEAP_MONTHS_BEFORE_SAKA: dict[int, int] = {}

# Published civil-date month windows (TNP / Shantideva / Buddha Weekly).
# Used when we have them so the first/last day match announcements.
SAKA_WINDOWS: dict[int, tuple[date, date]] = {
    2025: (date(2025, 5, 28), date(2025, 6, 25)),
    2026: (date(2026, 5, 17), date(2026, 6, 15)),
}


@dataclass(frozen=True)
class SakaDawaWindow:
    """Civil-date window for one Tibetan year's Saka Dawa."""

    tibetan_year: int
    losar: date
    month_start: date
    duchen: date
    month_end: date
    calendar: str = "phugpa-losar"

    def contains(self, day: date) -> bool:
        return self.month_start <= day <= self.month_end


def _as_date(value: datetime | date | None) -> date:
    if value is None:
        return datetime.now().date()
    if isinstance(value, datetime):
        return value.date()
    return value


def losar_for_year(year: int) -> date | None:
    """Return published Losar for a Gregorian year, if we have it."""
    return LOSAR_DATES.get(year)


def tibetan_year_for(day: date) -> int:
    """Gregorian year of the Losar that opened the current Tibetan year."""
    losar = LOSAR_DATES.get(day.year)
    if losar is not None and day < losar:
        return day.year - 1
    return day.year


def _offset_date(origin: date, synodic_months: float) -> date:
    return origin + timedelta(days=round(synodic_months * SYNODIC_DAYS))


def saka_dawa_window(tibetan_year: int) -> SakaDawaWindow | None:
    """Build the Saka Dawa window for the Tibetan year that begins at Losar."""
    losar = LOSAR_DATES.get(tibetan_year)
    if losar is None:
        return None

    extra = LEAP_MONTHS_BEFORE_SAKA.get(tibetan_year, 0)
    computed_duchen = _offset_date(losar, 3.5 + extra)
    published = DUCHEN_DATES.get(tibetan_year)
    # Prefer the published full moon. A >3-day drift from the 3.5-month
    # count means a leap month landed between Losar and Saka Dawa.
    duchen = published if published is not None else computed_duchen

    published_window = SAKA_WINDOWS.get(tibetan_year)
    if published_window is not None:
        month_start, month_end = published_window
    else:
        # Lunar month containing the full moon ≈ Duchen ± 14 days.
        month_start = duchen - timedelta(days=14)
        month_end = duchen + timedelta(days=14)

    return SakaDawaWindow(
        tibetan_year=tibetan_year,
        losar=losar,
        month_start=month_start,
        duchen=duchen,
        month_end=month_end,
        calendar="phugpa-losar",
    )


def _chinese_proxy(day: date) -> dict[str, Any] | None:
    """Last-resort proxy: Chinese lunar month 4 ≈ Saka Dawa.

    Only used when the date's Tibetan year is outside the Losar table.
    """
    try:
        from lunar_python import Lunar, Solar
    except ImportError:
        return None

    solar = Solar.fromYmd(day.year, day.month, day.day)
    lunar = Lunar.fromSolar(solar)
    lunar_month = lunar.getMonth()
    lunar_day = lunar.getDay()
    is_saka = abs(lunar_month) == 4
    is_duchen = is_saka and lunar_day == 15
    multiplier = 100000 if is_duchen else 10000 if is_saka else 1
    return {
        "is_saka_dawa": is_saka,
        "is_duchen": is_duchen,
        "multiplier": multiplier,
        "lunar_month": abs(lunar_month),
        "lunar_day": lunar_day,
        "calendar": "chinese_proxy",
        "losar": None,
        "saka_dawa_month_start": None,
        "saka_dawa_month_end": None,
        "saka_dawa_duchen": None,
        "days_until_saka_dawa": None,
        "days_until_duchen": None,
    }


def saka_dawa_status(target: datetime | date | None = None) -> dict[str, Any]:
    """Return Saka Dawa status for ``target`` (default: today, local date)."""
    day = _as_date(target)
    iso_now = (
        target.isoformat()
        if isinstance(target, datetime)
        else datetime.combine(day, datetime.min.time()).isoformat()
    )

    tib_year = tibetan_year_for(day)
    window = saka_dawa_window(tib_year)
    next_window = saka_dawa_window(tib_year + 1)

    if window is None:
        proxy = _chinese_proxy(day)
        if proxy is not None:
            proxy["current_date"] = iso_now
            return proxy
        return {
            "is_saka_dawa": False,
            "is_duchen": False,
            "multiplier": 1,
            "current_date": iso_now,
            "lunar_month": None,
            "lunar_day": None,
            "calendar": "unavailable",
            "error": "No Losar date for this year and lunar_python is not installed",
        }

    is_saka = window.contains(day)
    is_duchen = day == window.duchen
    if is_duchen:
        multiplier = 100000
    elif is_saka:
        multiplier = 10000
    else:
        multiplier = 1

    if day < window.month_start:
        days_until_saka = (window.month_start - day).days
    elif is_saka:
        days_until_saka = 0
    elif next_window is not None:
        days_until_saka = (next_window.month_start - day).days
    else:
        days_until_saka = None

    if day <= window.duchen:
        days_until_duchen = (window.duchen - day).days
        upcoming_duchen = window.duchen
    elif next_window is not None:
        days_until_duchen = (next_window.duchen - day).days
        upcoming_duchen = next_window.duchen
    else:
        days_until_duchen = None
        upcoming_duchen = window.duchen

    if window.month_start <= day <= window.month_end:
        lunar_day = (day - window.month_start).days + 1
        lunar_month = 4
    elif day < window.month_start:
        lunar_day = (day - window.losar).days + 1
        # Rough month index from Losar; good enough for display.
        lunar_month = max(1, min(3, 1 + (day - window.losar).days // 30))
    else:
        lunar_day = (day - window.month_end).days
        lunar_month = 4 + max(1, (day - window.month_end).days // 30)

    display = window if day <= window.month_end else (next_window or window)

    return {
        "is_saka_dawa": is_saka,
        "is_duchen": is_duchen,
        "multiplier": multiplier,
        "current_date": iso_now,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "losar": window.losar.isoformat(),
        "saka_dawa_month_start": display.month_start.isoformat(),
        "saka_dawa_month_end": display.month_end.isoformat(),
        "saka_dawa_duchen": upcoming_duchen.isoformat(),
        "days_until_saka_dawa": days_until_saka,
        "days_until_duchen": days_until_duchen,
        "calendar": window.calendar,
        "tibetan_year": window.tibetan_year,
    }
