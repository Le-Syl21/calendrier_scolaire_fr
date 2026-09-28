"""Fetch the académie's calendar once a day, keep the last good answer across restarts."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
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
    JOURS_PAR_DEFAUT,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
    USER_AGENT,
)
from .schedule import (
    SchoolCalendar,
    parse_days_off,
    parse_periods,
    public_holidays,
    weekdays_from_keys,
)

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=60)
# Last school year's summer is still needed in July and August.
_LOOK_BACK = timedelta(days=400)

type SchoolConfigEntry = ConfigEntry[SchoolCoordinator]


def _time(value: str | None, default: time) -> time:
    try:
        return time.fromisoformat(value) if value else default
    except ValueError:
        return default


class SchoolCoordinator(DataUpdateCoordinator[SchoolCalendar]):
    """One coordinator per school: académie, level and the school's own days."""

    config_entry: SchoolConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SchoolConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.academie: str = entry.data[CONF_ACADEMIE]
        self.niveau: str = entry.data[CONF_NIVEAU]
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._session = async_get_clientsession(hass)
        self._records: list[dict] = []
        self._fetched: str | None = None
        self._unsub_tick = None

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self._records = stored.get("records", [])
        self._fetched = stored.get("fetched")
        # "In class" and "school day" change with the clock, not with the
        # data: refresh the entities every minute without fetching anything.
        self._unsub_tick = async_track_time_change(self.hass, self._tick, second=0)

    @callback
    def _tick(self, _now: datetime) -> None:
        if self.data is not None:
            self.async_update_listeners()

    async def async_shutdown(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
        await super().async_shutdown()

    async def _fetch(self, today: date) -> list[dict] | None:
        since = (today - _LOOK_BACK).isoformat()
        params = {
            "where": f"location=\"{self.academie}\" and end_date>=date'{since}'",
            "order_by": "start_date",
            "limit": "100",
        }
        try:
            async with self._session.get(
                API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                body = await resp.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.warning("School calendar unavailable for %s: %s", self.academie, err)
            return None
        results = body.get("results") if isinstance(body, dict) else None
        if not isinstance(results, list):
            _LOGGER.warning("School calendar for %s not understood, ignored", self.academie)
            return None
        return results

    def build(self, records: list[dict]) -> SchoolCalendar:
        options = self.config_entry.options
        territoire = options.get(CONF_TERRITOIRE)
        periods = parse_periods(records, self.niveau, territoire)
        today = dt_util.now().date()
        years = {today.year - 1, today.year, today.year + 1, today.year + 2}
        years.update(y for p in periods for y in (p.first.year, p.last.year))
        try:
            days_off = parse_days_off(options.get(CONF_JOURS_SANS_CLASSE))
        except ValueError:
            days_off = set()  # validated in the options form; never lose the rest
        return SchoolCalendar(
            periods=periods,
            public_holidays=public_holidays(
                self.academie, years, options.get(CONF_MOSELLE, False), territoire
            ),
            weekdays=weekdays_from_keys(options.get(CONF_JOURS, JOURS_PAR_DEFAUT[self.niveau])),
            days_off=days_off,
            start=_time(options.get(CONF_DEBUT), DEBUT_PAR_DEFAUT),
            end=_time(options.get(CONF_FIN), FIN_PAR_DEFAUT),
            wednesday_end=_time(options.get(CONF_FIN_MERCREDI), FIN_MERCREDI_PAR_DEFAUT),
        )

    async def _async_update_data(self) -> SchoolCalendar:
        now = dt_util.now()
        if (records := await self._fetch(now.date())) is not None:
            self._records = records
            self._fetched = now.isoformat()
            await self._store.async_save({"records": records, "fetched": self._fetched})
        elif not self._records:
            raise UpdateFailed(f"No school calendar for {self.academie} yet")
        return await self.hass.async_add_executor_job(self.build, self._records)

    @property
    def fetched(self) -> str | None:
        return self._fetched
