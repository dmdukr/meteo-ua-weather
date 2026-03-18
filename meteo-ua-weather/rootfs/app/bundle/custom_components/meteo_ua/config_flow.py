"""Config flow for Meteo UA — single-step with live search from meteo.ua API."""
from __future__ import annotations

import logging
import re

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
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

AUTOCOMPLETE_URL = (
    "https://meteo.ua/front/forecast/autocomplete?phrase={phrase}&lang=ua"
)
MAX_RESULTS = 20
MIN_CHARS = 3
_URL_RE = re.compile(r"/ua/(\d+)/(.+)")


async def _fetch_cities(phrase: str) -> list[dict]:
    """Call meteo.ua autocomplete API, return list of {id, slug, title}."""
    url = AUTOCOMPLETE_URL.format(phrase=phrase)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
    except Exception:
        return []

    results = []
    for item in data[:MAX_RESULTS]:
        m = _URL_RE.search(item.get("url", ""))
        if m:
            results.append({
                "city_id": m.group(1),
                "slug": m.group(2),
                "title": item.get("title", m.group(2)),
            })
    return results


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Single-step config flow: type >= 3 chars, submit, pick from results."""

    VERSION = 2

    def __init__(self) -> None:
        self._cities: list[dict] = []
        self._last_phrase: str = ""

    async def async_step_user(self, user_input=None):
        """Single step: text search + optional dropdown with results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            city = user_input.get("city")
            phrase = user_input.get("phrase", "").strip()

            # User picked a city from dropdown → create entry
            if city:
                parts = city.split("/", 1)
                if len(parts) == 2:
                    city_id, slug = parts
                    title = next(
                        (c["title"] for c in self._cities if c["city_id"] == city_id),
                        slug,
                    )
                    await self.async_set_unique_id(f"meteo_ua_{city_id}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Meteo UA \u2014 {title}",
                        data={
                            CONF_CITY_ID: city_id,
                            CONF_CITY_SLUG: slug,
                            CONF_CITY_NAME: title,
                        },
                    )

            # No city selected — do search
            if len(phrase) < MIN_CHARS:
                errors["phrase"] = "too_short"
            else:
                self._last_phrase = phrase
                self._cities = await _fetch_cities(phrase)
                if not self._cities:
                    errors["phrase"] = "no_results"

        # Build dynamic schema
        schema_fields: dict = {
            vol.Required("phrase", default=self._last_phrase): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        }

        if self._cities:
            options = [
                SelectOptionDict(
                    value=f"{c['city_id']}/{c['slug']}",
                    label=c["title"],
                )
                for c in self._cities
            ]
            schema_fields[vol.Optional("city")] = SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )
