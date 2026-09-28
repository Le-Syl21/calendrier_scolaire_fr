"""What every entity of an entry shares."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import ACADEMIES, DOMAIN, OBJECT_IDS
from .coordinator import SchoolCoordinator

_NIVEAUX = {"primaire": "Maternelle et élémentaire", "college": "Collège", "lycee": "Lycée"}


class SchoolEntity(CoordinatorEntity[SchoolCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SchoolCoordinator, key: str, platform: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # Fixed French ids, the same whatever the language of Home Assistant,
        # prefixed by the school's name so several schools can coexist.
        self.entity_id = f"{platform}.{slugify(entry.title)}_{OBJECT_IDS[key]}"
        academie = coordinator.academie
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Éducation nationale",
            model=f"{_NIVEAUX[coordinator.niveau]} · {academie} ({ACADEMIES.get(academie, '?')})",
            entry_type=DeviceEntryType.SERVICE,
        )
