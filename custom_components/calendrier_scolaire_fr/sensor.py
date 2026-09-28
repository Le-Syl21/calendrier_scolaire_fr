"""Sensor: the next school holidays."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SchoolConfigEntry
from .entity import SchoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([NextHolidaysSensor(entry.runtime_data)])


class NextHolidaysSensor(SchoolEntity, SensorEntity):
    """First day of the next holidays; their name and length as attributes."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "next_holidays", "sensor")

    def _period(self):
        return self.coordinator.data.next_holidays(dt_util.now().date())

    @property
    def native_value(self):
        period = self._period()
        return period.first if period else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        period = self._period()
        if period is None:
            return {}
        today = dt_util.now().date()
        return {
            "nom": period.name,
            "dernier_jour": period.last.isoformat(),
            "reprise": period.end.isoformat(),
            "dans_jours": (period.first - today).days,
            "provisoire": period.provisional,
        }
