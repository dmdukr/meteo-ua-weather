"""DataUpdateCoordinator for Meteo UA."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_SLUG, CONF_STATION_ID, UPDATE_INTERVAL_CURRENT
from .parsers.meteo_gov_ua import async_fetch_current
from .parsers.meteo_ua import async_fetch_monthly

_LOGGER = logging.getLogger(__name__)


class MeteoUaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch current weather + 30-day forecast."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.city_id: str = entry.data[CONF_CITY_ID]
        self.city_slug: str = entry.data[CONF_CITY_SLUG]
        self.station_id: str = entry.data[CONF_STATION_ID]

        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{self.city_slug}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_CURRENT),
        )

        self._monthly: dict[str, Any] = {"forecast": [], "days": 0, "city": self.city_slug}
        self._tick: int = 0
        self._monthly_every: int = 4  # every 4th update = ~2h

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)

        try:
            current = await async_fetch_current(session, self.station_id)
        except Exception as exc:
            raise UpdateFailed(f"Current weather error: {exc}") from exc

        self._tick += 1
        if self._tick >= self._monthly_every or not self._monthly.get("forecast"):
            self._tick = 0
            try:
                lang = self.hass.config.language or "uk"
                self._monthly = await async_fetch_monthly(
                    session, self.city_id, self.city_slug, lang=lang,
                )
            except Exception as exc:
                _LOGGER.warning("Monthly forecast error: %s", exc)

        return {"current": current, "monthly": self._monthly}
