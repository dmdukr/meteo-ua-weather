"""Config flow for Meteo UA — single-step searchable dropdown."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_SLUG, CONF_CITY_NAME

_LOGGER = logging.getLogger(__name__)

_SETTLEMENTS: list[list] | None = None


def _load_settlements() -> list[list]:
    """Load settlements from bundled JSON (lazy, cached)."""
    global _SETTLEMENTS
    if _SETTLEMENTS is None:
        path = Path(__file__).parent / "settlements.json"
        with open(path, encoding="utf-8") as fh:
            _SETTLEMENTS = json.load(fh)
        _LOGGER.debug("Loaded %d settlements from %s", len(_SETTLEMENTS), path)
    return _SETTLEMENTS


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow — single searchable dropdown with 23 000+ settlements."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Single step: searchable dropdown."""
        errors = {}

        if user_input is not None:
            value = user_input.get("settlement", "")
            parts = value.split("/", 1)
            if len(parts) == 2 and parts[0].isdigit():
                city_id, city_slug = parts
                # Find title from settlements
                settlements = await self.hass.async_add_executor_job(_load_settlements)
                title = next(
                    (s[2] for s in settlements if str(s[0]) == city_id),
                    city_slug,
                )
                await self.async_set_unique_id(f"meteo_ua_{city_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Meteo UA \u2014 {title}",
                    data={
                        CONF_CITY_ID: city_id,
                        CONF_CITY_SLUG: city_slug,
                        CONF_CITY_NAME: title,
                    },
                )
            errors["settlement"] = "invalid_selection"

        settlements = await self.hass.async_add_executor_job(_load_settlements)
        options = [
            SelectOptionDict(
                value=f"{s[0]}/{s[1]}",
                label=s[2],
            )
            for s in settlements
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("settlement"): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )
