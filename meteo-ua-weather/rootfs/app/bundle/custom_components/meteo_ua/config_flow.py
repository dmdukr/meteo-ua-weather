"""Config flow for Meteo UA — two-step: filter then create."""
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

DEFAULT_CITIES: list[dict] = [
    {"city_id": "33345", "slug": "kyiv", "title": "Київ"},
    {"city_id": "33275", "slug": "kharkiv", "title": "Харків"},
    {"city_id": "33393", "slug": "odesa", "title": "Одеса"},
    {"city_id": "33466", "slug": "dnipro", "title": "Дніпро"},
    {"city_id": "33317", "slug": "donetsk", "title": "Донецьк"},
    {"city_id": "33310", "slug": "zaporizhzhia", "title": "Запоріжжя"},
    {"city_id": "33301", "slug": "lviv", "title": "Львів"},
    {"city_id": "33368", "slug": "kryvyi-rih", "title": "Кривий Ріг"},
    {"city_id": "33369", "slug": "mykolaiv", "title": "Миколаїв"},
    {"city_id": "33206", "slug": "sevastopol", "title": "Севастополь"},
    {"city_id": "33246", "slug": "mariupol", "title": "Маріуполь"},
    {"city_id": "33302", "slug": "luhansk", "title": "Луганськ"},
    {"city_id": "33261", "slug": "vinnytsia", "title": "Вінниця"},
    {"city_id": "33189", "slug": "simferopol", "title": "Сімферополь"},
    {"city_id": "33377", "slug": "kherson", "title": "Херсон"},
    {"city_id": "33325", "slug": "poltava", "title": "Полтава"},
    {"city_id": "33240", "slug": "chernihiv", "title": "Чернігів"},
    {"city_id": "33339", "slug": "cherkasy", "title": "Черкаси"},
    {"city_id": "33215", "slug": "zhytomyr", "title": "Житомир"},
    {"city_id": "33256", "slug": "sumy", "title": "Суми"},
]


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


def _build_options(cities: list[dict]) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=f"{c['city_id']}/{c['slug']}", label=c["title"])
        for c in cities
    ]


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step config flow: filter → select & create."""

    VERSION = 2

    def __init__(self) -> None:
        self._cities: list[dict] = DEFAULT_CITIES

    async def async_step_user(self, user_input=None):
        """Step 1: search / filter. Empty = show top 20."""
        errors: dict[str, str] = {}

        if user_input is not None:
            phrase = user_input.get("phrase", "").strip()

            if phrase:
                if len(phrase) < MIN_CHARS:
                    errors["phrase"] = "too_short"
                else:
                    results = await _fetch_cities(phrase)
                    if results:
                        self._cities = results
                    else:
                        errors["phrase"] = "no_results"
            else:
                self._cities = DEFAULT_CITIES

            if not errors:
                return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("phrase", default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
            }),
            errors=errors,
        )

    async def async_step_select(self, user_input=None):
        """Step 2: pick city from list → create entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            city = user_input.get("city")
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
            errors["city"] = "invalid_selection"

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({
                vol.Required("city"): SelectSelector(
                    SelectSelectorConfig(
                        options=_build_options(self._cities),
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )
