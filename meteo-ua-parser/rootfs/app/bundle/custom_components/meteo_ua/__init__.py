"""Meteo UA — weather from meteo.gov.ua + 30-day forecast from meteo.ua."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import MeteoUaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS_LIST = [Platform.WEATHER]

ADDON_SLUG = "05f6fddb_meteo_ua_parser"


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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when the last config entry is removed via UI.

    Removes integration from custom_components/ and notifies user.
    Card JS lives inside the integration dir, so it's removed together.
    """
    # Remove legacy card from www/ if exists
    legacy_card = Path(hass.config.path("www/meteo-ua-weather-forecast-card.js"))
    if legacy_card.exists():
        try:
            legacy_card.unlink()
            _LOGGER.info("Removed legacy card: %s", legacy_card)
        except OSError:
            pass

    # Remove integration from custom_components/
    integration_path = Path(__file__).parent  # custom_components/meteo_ua/
    if integration_path.exists():
        try:
            shutil.rmtree(integration_path)
            _LOGGER.info("Removed integration: %s", integration_path)
        except OSError as exc:
            _LOGGER.warning("Failed to remove integration: %s", exc)

    # Notify user about restart
    from homeassistant.components.persistent_notification import async_create
    async_create(
        hass,
        "Інтеграцію Meteo UA Weather видалено. "
        "**[Перезавантажте Home Assistant](/developer-tools/yaml)** для завершення.\n\n"
        "Meteo UA Weather integration removed. "
        "**[Restart Home Assistant](/developer-tools/yaml)** to complete removal.",
        title="Meteo UA Weather",
        notification_id="meteo_ua_removed",
    )


async def _register_card(hass: HomeAssistant) -> None:
    """Register the Lovelace card JS as a frontend module."""
    if hass.data.get(DOMAIN, {}).get("_card_registered"):
        return

    from homeassistant.components.http import StaticPathConfig
    from homeassistant.components.frontend import add_extra_js_url

    frontend_dir = Path(__file__).parent / "frontend"
    cards = {
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
