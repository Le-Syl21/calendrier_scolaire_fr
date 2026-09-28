"""Calendar: holidays, public holidays and the school's own days off."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SchoolConfigEntry
from .entity import SchoolEntity
from .schedule import SchoolCalendar


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SchoolCalendarEntity(entry.runtime_data)])


def _events(cal: SchoolCalendar, first: date, end: date) -> list[CalendarEvent]:
    """Every day without school other than the weekly ones, between `first` and `end`."""
    events = [
        CalendarEvent(start=p.first, end=p.end, summary=p.name)
        for p in cal.periods
        if p.first < end and p.end > first
    ]
    for day, name in cal.public_holidays.items():
        if first <= day < end:
            events.append(CalendarEvent(start=day, end=day + timedelta(days=1), summary=name))
    for day in cal.days_off:
        if first <= day < end:
            events.append(
                CalendarEvent(start=day, end=day + timedelta(days=1), summary="Jour sans classe")
            )
    return sorted(events, key=lambda e: (e.start, e.end))


class SchoolCalendarEntity(SchoolEntity, CalendarEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "calendar", "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        upcoming = _events(self.coordinator.data, today, today + timedelta(days=400))
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return _events(
            self.coordinator.data,
            dt_util.as_local(start_date).date(),
            dt_util.as_local(end_date).date() + timedelta(days=1),
        )
