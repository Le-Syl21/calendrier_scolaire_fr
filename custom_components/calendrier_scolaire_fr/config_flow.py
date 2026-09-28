"""Config flow: the school's académie and level, then its own week."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TimeSelector,
)

from .const import (
    ACADEMIES,
    CONF_ACADEMIE,
    CONF_DEBUT,
    CONF_FIN,
    CONF_FIN_MERCREDI,
    CONF_JOURS,
    CONF_JOURS_SANS_CLASSE,
    CONF_MOSELLE,
    CONF_NIVEAU,
    CONF_TERRITOIRE,
    DEBUT_PAR_DEFAUT,
    DOMAIN,
    FIN_MERCREDI_PAR_DEFAUT,
    FIN_PAR_DEFAUT,
    JOURS,
    JOURS_PAR_DEFAUT,
    NIVEAU_PRIMAIRE,
    NIVEAUX,
    TERRITOIRES,
)
from .schedule import parse_days_off

_ACADEMIE_OPTIONS = [
    SelectOptionDict(value=name, label=f"{name} ({zone})" if zone.startswith("Zone") else name)
    for name, zone in sorted(ACADEMIES.items(), key=lambda kv: (kv[1], kv[0]))
]


def _week_schema(academie: str, niveau: str, current: dict[str, Any]) -> dict[Any, Any]:
    """The fields of the school's own week, prefilled from `current`."""
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_JOURS, default=current.get(CONF_JOURS, JOURS_PAR_DEFAUT[niveau])
        ): SelectSelector(
            SelectSelectorConfig(
                options=list(JOURS[:6]),
                multiple=True,
                translation_key=CONF_JOURS,
                mode=SelectSelectorMode.LIST,
            )
        ),
        vol.Required(
            CONF_DEBUT, default=current.get(CONF_DEBUT, DEBUT_PAR_DEFAUT.isoformat())
        ): TimeSelector(),
        vol.Required(
            CONF_FIN, default=current.get(CONF_FIN, FIN_PAR_DEFAUT.isoformat())
        ): TimeSelector(),
        vol.Required(
            CONF_FIN_MERCREDI,
            default=current.get(CONF_FIN_MERCREDI, FIN_MERCREDI_PAR_DEFAUT.isoformat()),
        ): TimeSelector(),
    }
    if academie == "Nancy-Metz":
        schema[vol.Required(CONF_MOSELLE, default=current.get(CONF_MOSELLE, False))] = (
            BooleanSelector()
        )
    if academie == "Guadeloupe":
        schema[
            vol.Required(CONF_TERRITOIRE, default=current.get(CONF_TERRITOIRE, "guadeloupe"))
        ] = SelectSelector(
            SelectSelectorConfig(
                options=list(TERRITOIRES),
                translation_key=CONF_TERRITOIRE,
                mode=SelectSelectorMode.LIST,
            )
        )
    return schema


class SchoolConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._title = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._title = user_input.pop("nom").strip() or "École"
            self._data = user_input
            return await self.async_step_semaine()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("nom", default="École"): TextSelector(),
                    vol.Required(CONF_ACADEMIE): SelectSelector(
                        SelectSelectorConfig(
                            options=_ACADEMIE_OPTIONS, mode=SelectSelectorMode.DROPDOWN
                        )
                    ),
                    vol.Required(CONF_NIVEAU, default=NIVEAU_PRIMAIRE): SelectSelector(
                        SelectSelectorConfig(
                            options=list(NIVEAUX),
                            translation_key=CONF_NIVEAU,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_semaine(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=self._title, data=self._data, options=user_input)
        return self.async_show_form(
            step_id="semaine",
            data_schema=vol.Schema(
                _week_schema(self._data[CONF_ACADEMIE], self._data[CONF_NIVEAU], {})
            ),
            description_placeholders={"nom": self._title},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SchoolOptionsFlow()


class SchoolOptionsFlow(OptionsFlow):
    """The school's week and its own days off: what changes from year to year."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = dict(self.config_entry.options)
        if user_input is not None:
            try:
                parse_days_off(user_input.get(CONF_JOURS_SANS_CLASSE))
            except ValueError:
                errors[CONF_JOURS_SANS_CLASSE] = "invalid_days_off"
                current = user_input
            else:
                return self.async_create_entry(data=user_input)
        data = self.config_entry.data
        schema = _week_schema(data[CONF_ACADEMIE], data[CONF_NIVEAU], current)
        schema[
            vol.Optional(CONF_JOURS_SANS_CLASSE, default=current.get(CONF_JOURS_SANS_CLASSE, ""))
        ] = TextSelector(TextSelectorConfig(multiline=True))
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema), errors=errors)
