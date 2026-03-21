"""Meteo UA — weather + 30-day forecast from meteo.ua."""
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

CARD_FILENAME = "meteo-ua-weather-forecast-card.js"
CARD_URL = f"/local/{CARD_FILENAME}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version < 2:
        _LOGGER.info("Migrating Meteo UA config entry %s from v%s to v2", entry.entry_id, entry.version)
        new_data = dict(entry.data)
        new_data.pop("station_id", None)
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MeteoUaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_LIST)

    await _register_card(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_LIST)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up card resources when the last config entry is removed."""
    remaining = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if remaining:
        return

    # Last entry removed — unregister Lovelace resource and delete JS
    await _unregister_card(hass)


async def _register_card(hass: HomeAssistant) -> None:
    """Copy card JS to www/ and register as Lovelace resource."""
    if hass.data.get(DOMAIN, {}).get("_card_registered"):
        return

    # Copy JS to www/
    src = Path(__file__).parent / "frontend" / CARD_FILENAME
    www_dir = Path(hass.config.path("www"))
    www_dir.mkdir(exist_ok=True)
    dst = www_dir / CARD_FILENAME

    try:
        if not dst.exists() or src.stat().st_size != dst.stat().st_size:
            await hass.async_add_executor_job(shutil.copy2, str(src), str(dst))
            _LOGGER.info("Copied %s to %s", CARD_FILENAME, dst)
    except Exception as exc:
        _LOGGER.error("Failed to copy card: %s", exc)
        return

    # Register as Lovelace resource via lovelace ResourceStorageCollection
    try:
        from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data is None:
            _LOGGER.warning("Lovelace not loaded — add card resource manually: %s", CARD_URL)
            return

        resources: ResourceStorageCollection | None = getattr(lovelace_data, "resources", None)
        if resources is None:
            _LOGGER.warning("Lovelace resources not available — add manually: %s", CARD_URL)
            return

        # Check if already registered
        existing = [
            r for r in resources.async_items()
            if CARD_FILENAME in r.get("url", "")
        ]
        if not existing:
            await resources.async_create_item({"res_type": "module", "url": CARD_URL})
            _LOGGER.info("Registered Lovelace resource: %s", CARD_URL)
        else:
            _LOGGER.debug("Lovelace resource already registered")
    except ImportError:
        _LOGGER.warning("Cannot import lovelace resources — add card manually: %s", CARD_URL)
    except Exception as exc:
        _LOGGER.warning("Could not auto-register card: %s — add manually: %s", exc, CARD_URL)

    hass.data.setdefault(DOMAIN, {})["_card_registered"] = True


async def _unregister_card(hass: HomeAssistant) -> None:
    """Remove Lovelace resource and delete JS file from www/."""
    # Remove Lovelace resource
    try:
        from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data is not None:
            resources: ResourceStorageCollection | None = getattr(
                lovelace_data, "resources", None
            )
            if resources is not None:
                existing = [
                    r for r in resources.async_items()
                    if CARD_FILENAME in r.get("url", "")
                ]
                for resource in existing:
                    await resources.async_delete_item(resource["id"])
                    _LOGGER.info("Removed Lovelace resource: %s", resource.get("url"))
    except Exception as exc:
        _LOGGER.warning("Failed to remove Lovelace resource: %s", exc)

    # Delete JS file from www/
    dst = Path(hass.config.path("www")) / CARD_FILENAME
    try:
        if dst.exists():
            await hass.async_add_executor_job(dst.unlink)
            _LOGGER.info("Deleted %s", dst)
    except Exception as exc:
        _LOGGER.warning("Failed to delete card file: %s", exc)

    hass.data.get(DOMAIN, {}).pop("_card_registered", None)
