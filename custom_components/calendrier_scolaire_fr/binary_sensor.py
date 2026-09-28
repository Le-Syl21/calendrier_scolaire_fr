"""Binary sensors: school day today and tomorrow, in class right now, holidays."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SchoolConfigEntry, SchoolCoordinator
from .entity import SchoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SchoolDaySensor(coordinator, "school_day", 0),
            SchoolDaySensor(coordinator, "school_day_tomorrow", 1),
            InClassSensor(coordinator),
            HolidaysSensor(coordinator),
        ]
    )


class SchoolDaySensor(SchoolEntity, BinarySensorEntity):
    """On on a school day; says why not otherwise."""

    def __init__(self, coordinator: SchoolCoordinator, key: str, offset: int) -> None:
        super().__init__(coordinator, key, "binary_sensor")
        self._offset = offset

    def _day(self) -> date:
        return dt_util.now().date() + timedelta(days=self._offset)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_school_day(self._day())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        day = self._day()
        cal = self.coordinator.data
        status = cal.status(day)
        nxt = cal.next_school_day(day)
        return {
            "date": day.isoformat(),
            "motif": status.reason,
            "libelle": status.label,
            "prochain_jour_de_classe": nxt.isoformat() if nxt else None,
        }


class InClassSensor(SchoolEntity, BinarySensorEntity):
    """On during class hours of a school day."""

    def __init__(self, coordinator: SchoolCoordinator) -> None:
        super().__init__(coordinator, "in_class", "binary_sensor")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.in_class(dt_util.now())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        hours = self.coordinator.data.class_hours(dt_util.now().date())
        return {
            "debut": hours[0].isoformat("minutes") if hours else None,
            "fin": hours[1].isoformat("minutes") if hours else None,
        }


class HolidaysSensor(SchoolEntity, BinarySensorEntity):
    """On during school holidays and bridges of the national calendar."""

    def __init__(self, coordinator: SchoolCoordinator) -> None:
        super().__init__(coordinator, "holidays", "binary_sensor")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.current_holidays(dt_util.now().date()) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        period = self.coordinator.data.current_holidays(dt_util.now().date())
        if period is None:
            return {"nom": None, "premier_jour": None, "dernier_jour": None, "reprise": None}
        return {
            "nom": period.name,
            "premier_jour": period.first.isoformat(),
            "dernier_jour": period.last.isoformat(),
            "reprise": period.end.isoformat(),
            "provisoire": period.provisional,
        }
