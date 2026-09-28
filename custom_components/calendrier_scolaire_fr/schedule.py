"""School days from the Éducation nationale calendar, public holidays and the school's own days off.

Everything here is pure: records in, dates out. The coordinator fetches, the
entities read.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import holidays

from .const import (
    JOURS,
    NIVEAU_COLLEGE,
    NIVEAU_LYCEE,
    NIVEAU_PRIMAIRE,
    SUBDIVISION_MOSELLE,
    SUBDIVISIONS,
    SUBDIVISIONS_TERRITOIRE,
)

# The dataset gives every boundary as midnight in Paris, written in UTC, even
# for the overseas académies: 2026-10-16T22:00:00+00:00 is 17 October. Reading
# it in the local time zone of La Réunion would shift every date by a day.
PARIS = ZoneInfo("Europe/Paris")

# How long a period announced only by its first day ("Début des Vacances
# d'Été", published before the following school year is) is assumed to last.
_OPEN_SUMMER_END = (9, 1)  # metropolitan rentrée, at the latest
_OPEN_AUSTRAL_DAYS = 46  # Réunion's austral winter, Polynesia's long holidays

REASON_HOLIDAYS = "vacances"
REASON_PUBLIC_HOLIDAY = "ferie"
REASON_DAY_OFF = "jour_sans_classe"
REASON_WEEKDAY = "jour_sans_cours"


def _plain(text: str) -> str:
    """Lower case, no accents: population labels are not spelled consistently."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def population_applies(population: str | None, niveau: str, territoire: str | None) -> bool:
    """Whether a record's population covers pupils of `niveau` (and `territoire`)."""
    pop = _plain(population or "-")
    if pop in ("-", "", "eleves"):
        return True
    if "enseignant" in pop:
        return False
    if "guadeloupe" in pop or ("saint" in pop and ("martin" in pop or "barthelemy" in pop)):
        mine = {
            "guadeloupe": "guadeloupe",
            "saint_martin": "martin",
            "saint_barthelemy": "barthelemy",
        }[territoire or "guadeloupe"]
        if f"sauf saint-{mine}" in pop or f"sauf {mine}" in pop:
            return False
        return mine in pop
    levels = set()
    if "premier degre" in pop:
        levels.add(NIVEAU_PRIMAIRE)
    if "second degre" in pop:
        levels.update((NIVEAU_COLLEGE, NIVEAU_LYCEE))
    if "college" in pop:
        levels.add(NIVEAU_COLLEGE)
    if "lycee" in pop:
        levels.add(NIVEAU_LYCEE)
    return niveau in levels


def _paris_date(value: str) -> date:
    return datetime.fromisoformat(value).astimezone(PARIS).date()


@dataclass(frozen=True)
class Period:
    """Days without school from the national calendar: `first` to `end`, end excluded."""

    name: str
    first: date
    end: date
    provisional: bool = False

    def __contains__(self, day: date) -> bool:
        return self.first <= day < self.end

    @property
    def last(self) -> date:
        return self.end - timedelta(days=1)


def parse_periods(
    records: Iterable[dict], niveau: str, territoire: str | None = None
) -> list[Period]:
    """The periods that apply to pupils of `niveau`, in date order."""
    periods: set[Period] = set()
    for rec in records:
        if not population_applies(rec.get("population"), niveau, territoire):
            continue
        name = (rec.get("description") or "").strip()
        try:
            first = _paris_date(rec["start_date"])
            end = _paris_date(rec["end_date"])
        except (KeyError, TypeError, ValueError):
            continue
        provisional = False
        if end <= first:
            if name.startswith("Début des "):
                # Only the first day is known until the next school year is
                # published: assume the usual length.
                name = name.removeprefix("Début des ").strip()
                name = name[0].upper() + name[1:]
                if "austral" in name.lower() or "grandes" in name.lower():
                    end = first + timedelta(days=_OPEN_AUSTRAL_DAYS)
                else:
                    end = date(first.year, *_OPEN_SUMMER_END)
                    if end <= first:
                        end = first + timedelta(days=1)
                provisional = True
            else:
                # A single day (a bridge, a "journée vaquée") is published with
                # its start and end on the same midnight.
                end = first + timedelta(days=1)
        periods.add(Period(name, first, end, provisional))
    return sorted(periods, key=lambda p: (p.first, p.end, p.name))


def public_holidays(
    academie: str,
    years: Iterable[int],
    moselle: bool = False,
    territoire: str | None = None,
) -> dict[date, str]:
    subdiv = SUBDIVISIONS.get(academie)
    if academie == "Nancy-Metz" and moselle:
        subdiv = SUBDIVISION_MOSELLE
    if academie == "Guadeloupe" and territoire in SUBDIVISIONS_TERRITOIRE:
        subdiv = SUBDIVISIONS_TERRITOIRE[territoire]
    found = holidays.France(years=sorted(set(years)), subdiv=subdiv, language="fr")
    return dict(found.items())


_DATE = r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})"
_ITEM = re.compile(rf"^\s*{_DATE}\s*(?:(?:\.\.|au|->|→)\s*{_DATE})?\s*$", re.IGNORECASE)


def _parse_one(text: str) -> date:
    if "/" in text:
        d, m, y = (int(x) for x in text.split("/"))
        return date(y, m, d)
    return date.fromisoformat(text)


def parse_days_off(text: str | None) -> set[date]:
    """Days the school itself gives off: "2026-11-10, 07/05/2027 .. 10/05/2027".

    Raises ValueError on anything it does not understand, so the options form
    can say so instead of silently dropping a day.
    """
    days: set[date] = set()
    for item in re.split(r"[,;\n]", text or ""):
        if not item.strip():
            continue
        match = _ITEM.match(item)
        if not match:
            raise ValueError(item.strip())
        first = _parse_one(match.group(1))
        last = _parse_one(match.group(2)) if match.group(2) else first
        if last < first:
            raise ValueError(item.strip())
        days.update(first + timedelta(days=n) for n in range((last - first).days + 1))
    return days


@dataclass(frozen=True)
class DayStatus:
    school: bool
    reason: str | None = None
    label: str | None = None


@dataclass
class SchoolCalendar:
    periods: list[Period]
    public_holidays: dict[date, str]
    weekdays: frozenset[int]
    days_off: set[date] = field(default_factory=set)
    start: time = time(8, 30)
    end: time = time(16, 30)
    wednesday_end: time = time(12, 0)

    def period_on(self, day: date) -> Period | None:
        return next((p for p in self.periods if day in p), None)

    def status(self, day: date) -> DayStatus:
        if day in self.days_off:
            return DayStatus(False, REASON_DAY_OFF, "Jour sans classe")
        if name := self.public_holidays.get(day):
            return DayStatus(False, REASON_PUBLIC_HOLIDAY, name)
        if period := self.period_on(day):
            return DayStatus(False, REASON_HOLIDAYS, period.name)
        if day.weekday() not in self.weekdays:
            return DayStatus(False, REASON_WEEKDAY, JOURS_LONGS[day.weekday()])
        return DayStatus(True)

    def is_school_day(self, day: date) -> bool:
        return self.status(day).school

    def next_school_day(self, after: date, limit: int = 120) -> date | None:
        for n in range(1, limit + 1):
            day = after + timedelta(days=n)
            if self.is_school_day(day):
                return day
        return None

    def class_hours(self, day: date) -> tuple[time, time] | None:
        if not self.is_school_day(day):
            return None
        return self.start, self.wednesday_end if day.weekday() == 2 else self.end

    def in_class(self, now: datetime) -> bool:
        hours = self.class_hours(now.date())
        return hours is not None and hours[0] <= now.time() < hours[1]

    def current_holidays(self, day: date) -> Period | None:
        return self.period_on(day)

    def next_holidays(self, day: date) -> Period | None:
        return next((p for p in self.periods if p.first > day), None)


JOURS_LONGS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")


def weekdays_from_keys(keys: Iterable[str]) -> frozenset[int]:
    return frozenset(JOURS.index(k) for k in keys if k in JOURS)
