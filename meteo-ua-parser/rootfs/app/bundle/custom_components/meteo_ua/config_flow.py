"""Config flow for Meteo UA — live search via meteo.ua autocomplete."""
from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_SLUG, CONF_CITY_NAME, AUTOCOMPLETE_URL

_LOGGER = logging.getLogger(__name__)

MIN_QUERY_LENGTH = 2
MAX_RESULTS = 20


async def _search_settlements(session: aiohttp.ClientSession, query: str) -> list[dict]:
    """Call meteo.ua autocomplete API and return list of settlements."""
    url = AUTOCOMPLETE_URL.format(phrase=quote(query))
    try:
        async with session.get(
            url,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "HomeAssistant/MeteoUA",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
            if not isinstance(data, list):
                return []
            return data[:MAX_RESULTS]
    except Exception as exc:
        _LOGGER.warning("meteo.ua autocomplete failed: %s", exc)
        return []


def _parse_settlement(item: dict) -> dict | None:
    """Parse autocomplete item into city config dict."""
    url = item.get("url", "")
    title = item.get("title", "")
    slug = item.get("id", "")
    if not url or not title:
        return None
    # url format: /441/novoselovka -> city_id=441
    parts = url.strip("/").split("/")
    if len(parts) < 2 or not parts[0].isdigit():
        return None
    return {
        CONF_CITY_ID: parts[0],
        CONF_CITY_SLUG: parts[1],
        CONF_CITY_NAME: title,
    }


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow — search for settlement via meteo.ua."""

    VERSION = 2

    def __init__(self) -> None:
        self._search_results: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Step 1: user enters search query."""
        errors = {}

        if user_input is not None:
            query = user_input.get("query", "").strip()
            if len(query) < MIN_QUERY_LENGTH:
                errors["query"] = "too_short"
            else:
                session = async_get_clientsession(self.hass)
                results = await _search_settlements(session, query)
                if not results:
                    errors["query"] = "no_results"
                else:
                    self._search_results = []
                    for item in results:
                        parsed = _parse_settlement(item)
                        if parsed:
                            self._search_results.append(parsed)
                    if not self._search_results:
                        errors["query"] = "no_results"
                    else:
                        return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("query"): str,
            }),
            errors=errors,
        )

    async def async_step_select(self, user_input=None):
        """Step 2: user selects settlement from search results."""
        if user_input is not None:
            selected_name = user_input[CONF_CITY_NAME]
            city = next(
                (c for c in self._search_results if c[CONF_CITY_NAME] == selected_name),
                None,
            )
            if city:
                await self.async_set_unique_id(f"meteo_ua_{city[CONF_CITY_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Meteo UA — {city[CONF_CITY_NAME]}",
                    data=city,
                )

        options = [c[CONF_CITY_NAME] for c in self._search_results]
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({
                vol.Required(CONF_CITY_NAME): vol.In(options),
            }),
        )
