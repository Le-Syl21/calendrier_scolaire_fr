"""Config flow and entities in a running Home Assistant, network mocked."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.calendrier_scolaire_fr.const import API_URL, DOMAIN

from .conftest import records

PARIS = ZoneInfo("Europe/Paris")
PREFIX = "ecole_de_leon"


@pytest.fixture
def api(aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(API_URL, json={"results": records("versailles")})
    return aioclient_mock


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Paris")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="École de Léon",
        data={"academie": "Versailles", "niveau": "primaire"},
        options=options
        or {
            "jours": ["lun", "mar", "jeu", "ven"],
            "debut": "08:30:00",
            "fin": "16:30:00",
            "fin_mercredi": "12:00:00",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def state(hass: HomeAssistant, entity_id: str):
    st = hass.states.get(entity_id)
    assert st is not None, entity_id
    return st


async def test_config_flow(hass: HomeAssistant, api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nom": "École de Léon", "academie": "Versailles", "niveau": "primaire"}
    )
    assert result["step_id"] == "semaine"
    # The level's usual week is offered: no Wednesday in primary.
    defaults = {str(k): k.default() for k in result["data_schema"].schema if hasattr(k, "default")}
    assert defaults["jours"] == ["lun", "mar", "jeu", "ven"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "jours": ["lun", "mar", "jeu", "ven"],
            "debut": "08:30:00",
            "fin": "16:30:00",
            "fin_mercredi": "12:00:00",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "École de Léon"
    assert result["data"] == {"academie": "Versailles", "niveau": "primaire"}


async def test_moselle_asked_only_in_nancy_metz(hass: HomeAssistant, api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nom": "Collège", "academie": "Nancy-Metz", "niveau": "college"}
    )
    fields = {str(k) for k in result["data_schema"].schema}
    assert "moselle" in fields and "territoire" not in fields
    defaults = {str(k): k.default() for k in result["data_schema"].schema if hasattr(k, "default")}
    assert "mer" in defaults["jours"]


async def test_school_day_in_class(
    hass: HomeAssistant, api, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime(2026, 10, 15, 10, 0, tzinfo=PARIS))  # Thursday
    await _setup(hass)
    assert state(hass, f"binary_sensor.{PREFIX}_jour_de_classe").state == "on"
    assert state(hass, f"binary_sensor.{PREFIX}_en_classe").state == "on"
    assert state(hass, f"binary_sensor.{PREFIX}_vacances").state == "off"
    # Friday 16 is the last day before the Toussaint holidays.
    assert state(hass, f"binary_sensor.{PREFIX}_demain_jour_de_classe").state == "on"
    nxt = state(hass, f"sensor.{PREFIX}_prochaines_vacances")
    assert nxt.state == "2026-10-17"
    assert nxt.attributes["nom"] == "Vacances de la Toussaint"
    assert nxt.attributes["reprise"] == "2026-11-02"


async def test_holidays_and_wednesday(
    hass: HomeAssistant, api, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime(2026, 10, 21, 9, 0, tzinfo=PARIS))
    await _setup(hass)
    day = state(hass, f"binary_sensor.{PREFIX}_jour_de_classe")
    assert day.state == "off"
    assert day.attributes["motif"] == "vacances"
    assert day.attributes["libelle"] == "Vacances de la Toussaint"
    assert day.attributes["prochain_jour_de_classe"] == "2026-11-02"
    assert state(hass, f"binary_sensor.{PREFIX}_vacances").state == "on"
    assert state(hass, f"binary_sensor.{PREFIX}_en_classe").state == "off"


async def test_clock_moves_the_states(
    hass: HomeAssistant, api, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime(2026, 9, 29, 16, 29, 0, tzinfo=PARIS))  # Tuesday
    await _setup(hass)
    assert state(hass, f"binary_sensor.{PREFIX}_en_classe").state == "on"
    freezer.tick(60)
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert state(hass, f"binary_sensor.{PREFIX}_en_classe").state == "off"
    # Wednesday is not a school day in this primary school.
    assert state(hass, f"binary_sensor.{PREFIX}_demain_jour_de_classe").state == "off"


async def test_calendar_events(hass: HomeAssistant, api, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(datetime(2026, 9, 28, 9, 0, tzinfo=PARIS))
    await _setup(hass)
    cal = state(hass, f"calendar.{PREFIX}_calendrier")
    assert cal.attributes["message"] == "Vacances de la Toussaint"
    events = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": f"calendar.{PREFIX}_calendrier",
            "start_date_time": "2026-11-01 00:00:00",
            "end_date_time": "2026-11-30 00:00:00",
        },
        blocking=True,
        return_response=True,
    )
    summaries = [e["summary"] for e in events[f"calendar.{PREFIX}_calendrier"]["events"]]
    assert summaries == ["Vacances de la Toussaint", "Toussaint", "Armistice"]


async def test_api_down_keeps_the_last_answer(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(datetime(2026, 10, 21, 9, 0, tzinfo=PARIS))
    aioclient_mock.get(API_URL, json={"results": records("versailles")})
    entry = await _setup(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, status=503)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, f"binary_sensor.{PREFIX}_vacances").state == "on"


async def test_options_days_off(hass: HomeAssistant, api, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(datetime(2026, 11, 10, 9, 0, tzinfo=PARIS))  # Tuesday
    entry = await _setup(hass)
    assert state(hass, f"binary_sensor.{PREFIX}_jour_de_classe").state == "on"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    base = {
        "jours": ["lun", "mar", "jeu", "ven"],
        "debut": "08:30:00",
        "fin": "16:30:00",
        "fin_mercredi": "12:00:00",
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**base, "jours_sans_classe": "demain"}
    )
    assert result["errors"] == {"jours_sans_classe": "invalid_days_off"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**base, "jours_sans_classe": "10/11/2026"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    day = state(hass, f"binary_sensor.{PREFIX}_jour_de_classe")
    assert day.state == "off" and day.attributes["motif"] == "jour_sans_classe"
