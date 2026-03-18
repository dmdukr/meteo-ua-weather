"""Parser for meteo.ua — current weather + hourly from city page JSON."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import aiohttp

from ..const import ICON_TO_HA_CONDITION

_LOGGER = logging.getLogger(__name__)

CITY_PAGE_URL = "https://meteo.ua/ua/{city_id}/{city_slug}"

_UA_TZ = timezone(timedelta(hours=2))

_CARDINALS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _deg_to_cardinal(deg: float) -> str:
    idx = round(deg / 22.5) % 16
    return _CARDINALS[idx]


def _map_icon_to_condition(icon: str) -> str:
    if not icon:
        return "cloudy"
    for key, cond in ICON_TO_HA_CONDITION.items():
        if key in icon:
            return cond
    return "cloudy"


def _find_current_hour(data: dict) -> dict[str, Any] | None:
    now = datetime.now(_UA_TZ)
    current_hour = now.strftime("%H:00")
    today_key = now.strftime("%Y-%m-%d")

    if today_key in data:
        hours = data[today_key]
        if current_hour in hours:
            return hours[current_hour]
        best = None
        for h_str, h_data in hours.items():
            if h_str <= current_hour:
                if best is None or h_str > best[0]:
                    best = (h_str, h_data)
        if best:
            return best[1]
        if hours:
            return next(iter(hours.values()))

    for _day_key, hours in data.items():
        if hours:
            return next(iter(hours.values()))
    return None


def _parse_current(entry: dict[str, Any]) -> dict[str, Any]:
    wc = entry.get("weather_condition", {})
    icon = wc.get("icon", "")
    wind_deg = entry.get("wind_deg", 0) or 0

    return {
        "temperature": entry.get("temp"),
        "humidity": entry.get("humidity_value"),
        "pressure": entry.get("pressure_value"),
        "wind_speed": entry.get("wind_speed"),
        "wind_bearing": wind_deg,
        "wind_direction": _deg_to_cardinal(wind_deg),
        "condition": _map_icon_to_condition(icon),
        "condition_text": wc.get("description", ""),
    }


def _parse_hourly(data: dict) -> list[dict[str, Any]]:
    """Parse weatherDetailSlider into hourly forecast list."""
    hourly = []
    for day_key in sorted(data.keys()):
        hours = data[day_key]
        for hour_key in sorted(hours.keys()):
            entry = hours[hour_key]
            wc = entry.get("weather_condition", {})
            icon = wc.get("icon", "")
            wind_deg = entry.get("wind_deg", 0) or 0

            hourly.append({
                "datetime": f"{day_key}T{hour_key}:00+02:00",
                "temperature": entry.get("temp"),
                "humidity": entry.get("humidity_value"),
                "pressure": entry.get("pressure_value"),
                "wind_speed": entry.get("wind_speed"),
                "wind_bearing": wind_deg,
                "condition": _map_icon_to_condition(icon),
                "condition_text": wc.get("description", ""),
                "precipitation": entry.get("precipitation_value"),
            })
    return hourly


async def async_fetch_current_meteo_ua(
    session: aiohttp.ClientSession, city_id: str, city_slug: str,
) -> dict[str, Any]:
    """Fetch current weather + hourly data from meteo.ua city page."""
    url = CITY_PAGE_URL.format(city_id=city_id, city_slug=city_slug)
    try:
        async with session.get(
            url,
            headers={"User-Agent": "HomeAssistant/MeteoUA"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            resp.raise_for_status()
            html = await resp.text(encoding="utf-8", errors="replace")

        m = re.search(r"weatherDetailSlider\s*=\s*(\{.+?\});\s*(?:var|let|const|<)", html, re.DOTALL)
        if not m:
            _LOGGER.warning("No weatherDetailSlider found on meteo.ua/%s/%s", city_id, city_slug)
            return {**_empty(), "hourly": []}

        data = json.loads(m.group(1))
        entry = _find_current_hour(data)
        current = _parse_current(entry) if entry else _empty()
        hourly = _parse_hourly(data)

        return {**current, "hourly": hourly}

    except Exception as exc:
        _LOGGER.error("meteo.ua current fetch failed: %s", exc)
        return {**_empty(), "hourly": []}


def _empty() -> dict[str, Any]:
    return {
        "temperature": None, "humidity": None, "pressure": None,
        "wind_speed": None, "wind_bearing": 0,
        "condition": "unknown", "condition_text": "",
    }
