"""Config flow for Meteo UA — search + select dropdown."""
from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_SLUG, CONF_CITY_NAME

_LOGGER = logging.getLogger(__name__)

AUTOCOMPLETE_URL = "https://meteo.ua/front/forecast/autocomplete?phrase={phrase}"
MAX_RESULTS = 30


async def _search_settlements(session: aiohttp.ClientSession, query: str) -> list[dict]:
    """Call meteo.ua autocomplete API (Ukrainian) and return parsed settlements."""
    url = AUTOCOMPLETE_URL.format(phrase=quote(query))
    try:
        async with session.get(
            url,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "HomeAssistant/MeteoUA",
                "lang": "ua",
                "format": "json",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            if not isinstance(data, list):
                return []
    except Exception as exc:
        _LOGGER.warning("meteo.ua autocomplete failed: %s", exc)
        return []

    results = []
    for item in data[:MAX_RESULTS]:
        url_path = item.get("url", "")
        title = item.get("title", "")
        if not url_path or not title:
            continue
        # With lang:ua, url is "/ua/34/kiev" — strip /ua/ prefix
        path = url_path.strip("/")
        if path.startswith("ua/"):
            path = path[3:]
        parts = path.split("/")
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        results.append({
            CONF_CITY_ID: parts[0],
            CONF_CITY_SLUG: parts[1],
            CONF_CITY_NAME: title,
        })
    return results


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow — search for settlement, then select from dropdown."""

    VERSION = 2

    def __init__(self) -> None:
        self._results: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Step 1: enter settlement name."""
        errors = {}

        if user_input is not None:
            query = user_input.get("query", "").strip()
            if len(query) < 2:
                errors["query"] = "too_short"
            else:
                session = async_get_clientsession(self.hass)
                self._results = await _search_settlements(session, query)
                if not self._results:
                    errors["query"] = "no_results"
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("query"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
            }),
            errors=errors,
        )

    async def async_step_select(self, user_input=None):
        """Step 2: select settlement from search results."""
        if user_input is not None:
            value = user_input.get("settlement", "")
            city = next(
                (c for c in self._results
                 if f"{c[CONF_CITY_ID]}/{c[CONF_CITY_SLUG]}" == value),
                None,
            )
            if city:
                await self.async_set_unique_id(f"meteo_ua_{city[CONF_CITY_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Meteo UA \u2014 {city[CONF_CITY_NAME]}",
                    data=city,
                )

        options = [
            SelectOptionDict(
                value=f"{c[CONF_CITY_ID]}/{c[CONF_CITY_SLUG]}",
                label=c[CONF_CITY_NAME],
            )
            for c in self._results
        ]

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({
                vol.Required("settlement"): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
        )
