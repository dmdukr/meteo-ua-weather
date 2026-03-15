"""Meteo UA — weather from meteo.gov.ua + 30-day forecast from meteo.ua."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import MeteoUaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST = [Platform.WEATHER, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML — not used, config_flow only."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Meteo UA from a config entry."""
    coordinator = MeteoUaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_LIST)

    await _register_card(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_LIST)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok


async def _register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace card JS as a frontend module."""
    if hass.data.get(DOMAIN, {}).get("_card_registered"):
        return

    from homeassistant.components.http import StaticPathConfig
    from homeassistant.components.frontend import add_extra_js_url

    frontend_dir = Path(__file__).parent / "frontend"
    cards = {
        "/meteo_ua/meteo-monthly-card.js": "meteo-monthly-card.js",
        "/meteo_ua/atmospheric-weather-card.js": "atmospheric-weather-card.js",
        "/meteo_ua/meteo-ua-weather-forecast-card.js": "meteo-ua-weather-forecast-card.js",
    }

    await hass.http.async_register_static_paths([
        StaticPathConfig(url_path=url, path=str(frontend_dir / filename), cache_headers=True)
        for url, filename in cards.items()
    ])
    for url in cards:
        add_extra_js_url(hass, url)

    hass.data.setdefault(DOMAIN, {})["_card_registered"] = True
    _LOGGER.info("Meteo UA: registered %d frontend cards", len(cards))
