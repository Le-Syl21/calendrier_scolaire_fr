"""School days from real API answers."""

from datetime import date, datetime, time

import pytest

from custom_components.calendrier_scolaire_fr.schedule import (
    PARIS,
    REASON_DAY_OFF,
    REASON_HOLIDAYS,
    REASON_PUBLIC_HOLIDAY,
    REASON_WEEKDAY,
    SchoolCalendar,
    parse_days_off,
    parse_periods,
    population_applies,
    public_holidays,
    weekdays_from_keys,
)

from .conftest import records

PRIMAIRE = weekdays_from_keys(["lun", "mar", "jeu", "ven"])


def calendar(
    academie="Versailles", fixture="versailles", niveau="primaire", **kw
) -> SchoolCalendar:
    periods = parse_periods(records(fixture), niveau)
    return SchoolCalendar(
        periods=periods,
        public_holidays=public_holidays(academie, range(2025, 2029), kw.pop("moselle", False)),
        weekdays=kw.pop("weekdays", PRIMAIRE),
        **kw,
    )


def test_toussaint_2026_zone_c():
    cal = calendar()
    # Last day of class on Friday 16 October, back on Monday 2 November.
    assert cal.is_school_day(date(2026, 10, 16))
    for day in (date(2026, 10, 17), date(2026, 10, 19), date(2026, 10, 30), date(2026, 11, 1)):
        status = cal.status(day)
        assert not status.school
    assert cal.status(date(2026, 10, 19)).reason == REASON_HOLIDAYS
    assert cal.status(date(2026, 10, 19)).label == "Vacances de la Toussaint"
    assert cal.is_school_day(date(2026, 11, 2))


def test_wednesday_and_weekend_off_in_primary():
    cal = calendar()
    wednesday = date(2026, 9, 30)
    assert cal.status(wednesday) == cal.status(wednesday).__class__(
        False, REASON_WEEKDAY, "Mercredi"
    )
    assert not cal.is_school_day(date(2026, 10, 3))  # Saturday
    college = calendar(
        niveau="college", weekdays=weekdays_from_keys(["lun", "mar", "mer", "jeu", "ven"])
    )
    assert college.is_school_day(wednesday)


def test_public_holiday_outside_holidays():
    cal = calendar()
    status = cal.status(date(2026, 11, 11))  # Wednesday, but a holiday first
    assert status.reason == REASON_PUBLIC_HOLIDAY and status.label == "Armistice"
    assert cal.status(date(2027, 5, 17)).reason == REASON_PUBLIC_HOLIDAY  # Lundi de Pentecôte


def test_ascension_bridge_is_a_period():
    cal = calendar()
    # 2026: Ascension on Thursday 14 May, bridge on Friday 15, back on Monday 18.
    assert cal.status(date(2026, 5, 14)).reason == REASON_PUBLIC_HOLIDAY
    assert cal.status(date(2026, 5, 15)).label == "Pont de l'Ascension"
    assert cal.is_school_day(date(2026, 5, 18))
    # 2027 is published with start == end: a single day, Friday 7 May.
    assert cal.status(date(2027, 5, 7)).label == "Pont de l'Ascension"
    assert cal.is_school_day(date(2027, 5, 10))


def test_summer_uses_the_pupils_dates_not_the_teachers():
    cal = calendar()
    # Teachers are back on 31 August 2026, pupils on 1 September.
    assert cal.status(date(2026, 8, 31)).reason == REASON_HOLIDAYS
    assert cal.is_school_day(date(2026, 9, 1))


def test_alsace_and_moselle_holidays():
    alsace = calendar("Strasbourg", "strasbourg")
    assert alsace.status(date(2027, 3, 26)).label == "Vendredi saint"
    paris = calendar()
    assert paris.is_school_day(date(2027, 3, 26))
    moselle = public_holidays("Nancy-Metz", [2027], moselle=True)
    assert date(2027, 3, 26) in moselle
    assert date(2027, 3, 26) not in public_holidays("Nancy-Metz", [2027])


@pytest.mark.parametrize(
    ("population", "primaire", "college", "lycee"),
    [
        ("-", True, True, True),
        ("Élèves", True, True, True),
        ("Enseignants", False, False, False),
        ("Élèves du premier degré", True, False, False),
        ("Premier degré et collèges", True, True, False),
        ("Élèves du second degré", False, True, True),
        ("Élèves des lycées", False, False, True),
        ("Enseignants du premier degré", False, False, False),
    ],
)
def test_population_by_level(population, primaire, college, lycee):
    assert population_applies(population, "primaire", None) is primaire
    assert population_applies(population, "college", None) is college
    assert population_applies(population, "lycee", None) is lycee


def test_guadeloupe_territories():
    assert population_applies("Guadeloupe sauf Saint-Martin", "primaire", "guadeloupe")
    assert not population_applies("Guadeloupe sauf Saint-Martin", "primaire", "saint_martin")
    assert population_applies("Saint-Martin", "primaire", "saint_martin")
    assert not population_applies("Saint-Barthélémy", "primaire", "saint_martin")


def test_polynesia_levels_differ():
    primaire = parse_periods(records("polynesie"), "primaire")
    lycee = parse_periods(records("polynesie"), "lycee")
    summer = lambda periods: next(
        p for p in periods if p.name == "Grandes Vacances" and p.first.year == 2027
    )
    # Primary pupils leave a day before secondary ones in 2027.
    assert summer(primaire).first == date(2027, 7, 2)
    assert summer(lycee).first == date(2027, 7, 3)


def test_overseas_dates_are_read_in_paris_time():
    periods = parse_periods(records("reunion"), "primaire")
    first = next(
        p for p in periods if p.name == "Vacances après 1ère période" and p.first.year == 2026
    )
    assert (first.first, first.end) == (date(2026, 10, 10), date(2026, 10, 26))
    winter = next(
        p for p in periods if p.name.startswith("Vacances d'Hiver austral") and p.first.year == 2027
    )
    assert winter.provisional and winter.first == date(2027, 7, 3)


def test_days_off_typed_by_hand():
    assert parse_days_off("2026-11-10, 07/05/2027 .. 10/05/2027") == {
        date(2026, 11, 10),
        date(2027, 5, 7),
        date(2027, 5, 8),
        date(2027, 5, 9),
        date(2027, 5, 10),
    }
    assert parse_days_off("") == set()
    with pytest.raises(ValueError):
        parse_days_off("demain")
    with pytest.raises(ValueError):
        parse_days_off("2027-05-10 .. 2027-05-07")
    cal = calendar(days_off={date(2026, 11, 10)})
    assert cal.status(date(2026, 11, 10)).reason == REASON_DAY_OFF


def test_class_hours_and_next_day():
    cal = calendar(
        weekdays=weekdays_from_keys(["lun", "mar", "mer", "jeu", "ven"]),
        start=time(8, 30),
        end=time(16, 30),
        wednesday_end=time(11, 30),
    )
    assert cal.in_class(datetime(2026, 9, 29, 10, 0, tzinfo=PARIS))
    assert not cal.in_class(datetime(2026, 9, 29, 16, 30, tzinfo=PARIS))
    assert not cal.in_class(datetime(2026, 9, 30, 13, 0, tzinfo=PARIS))  # Wednesday afternoon
    assert cal.next_school_day(date(2026, 10, 16)) == date(2026, 11, 2)
    assert cal.next_holidays(date(2026, 9, 28)).name == "Vacances de la Toussaint"
