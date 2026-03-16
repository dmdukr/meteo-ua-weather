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
    # Clean up addon restart marker if exists (restart already happened)
    marker = Path(hass.config.path(".meteo_ua_restart_required"))
    if marker.exists():
        marker.unlink(missing_ok=True)
        # Dismiss the persistent notification since restart completed
        from homeassistant.components.persistent_notification import async_dismiss
        async_dismiss(hass, "meteo_ua_restart_required")
        _LOGGER.info("Restart completed — cleaned up marker and notification")
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
    # Remove Lovelace resource
    card_url = "/meteo_ua/meteo-ua-weather-forecast-card.js"
    try:
        from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data and hasattr(lovelace_data, "resources"):
            resources = lovelace_data.resources
            for item in resources.async_items():
                if card_url in item.get("url", ""):
                    await resources.async_delete_item(item["id"])
                    _LOGGER.info("Removed Lovelace resource: %s", card_url)
                    break
    except Exception as exc:
        _LOGGER.warning("Failed to remove Lovelace resource: %s", exc)

    # Remove legacy card from www/ if exists
    legacy_card = Path(hass.config.path("www/meteo-ua-weather-forecast-card.js"))
    if legacy_card.exists():
        try:
            legacy_card.unlink()
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
    """Register the Lovelace card JS as a Lovelace resource with cache-busting."""
    if hass.data.get(DOMAIN, {}).get("_card_registered"):
        return

    import json as _json
    from homeassistant.components.http import StaticPathConfig

    frontend_dir = Path(__file__).parent / "frontend"
    card_base_url = "/meteo_ua/meteo-ua-weather-forecast-card.js"
    card_file = "meteo-ua-weather-forecast-card.js"

    # Get version for cache-busting
    try:
        manifest = _json.loads((Path(__file__).parent / "manifest.json").read_text())
        version = manifest.get("version", "0")
    except Exception:
        version = "0"
    card_url = f"{card_base_url}?v={version}"

    # Register static path so the JS file is served by HA
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path=card_base_url,
            path=str(frontend_dir / card_file),
            cache_headers=False,
        )
    ])

    # Register as Lovelace resource (appears in Settings → Dashboards → Resources)
    try:
        from homeassistant.components.lovelace import (
            DOMAIN as LOVELACE_DOMAIN,
        )
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data and hasattr(lovelace_data, "resources"):
            resources: ResourceStorageCollection = lovelace_data.resources
            # Find existing registration (match base URL without version)
            existing = [
                r for r in resources.async_items()
                if card_base_url in r.get("url", "")
            ]
            if not existing:
                await resources.async_create_item({
                    "res_type": "module",
                    "url": card_url,
                })
                _LOGGER.info("Meteo UA: registered card as Lovelace resource (%s)", card_url)
            elif existing[0].get("url") != card_url:
                # Version changed — update URL for cache-busting
                await resources.async_update_item(existing[0]["id"], {
                    "res_type": "module",
                    "url": card_url,
                })
                _LOGGER.info("Meteo UA: updated card resource URL (%s)", card_url)
            else:
                _LOGGER.info("Meteo UA: card already in Lovelace resources")
        else:
            _LOGGER.warning("Meteo UA: Lovelace resources not available, using add_extra_js_url")
            from homeassistant.components.frontend import add_extra_js_url
            add_extra_js_url(hass, card_url)
    except Exception as exc:
        _LOGGER.warning("Meteo UA: failed to register Lovelace resource (%s), using add_extra_js_url", exc)
        from homeassistant.components.frontend import add_extra_js_url
        add_extra_js_url(hass, card_url)

    hass.data.setdefault(DOMAIN, {})["_card_registered"] = True
