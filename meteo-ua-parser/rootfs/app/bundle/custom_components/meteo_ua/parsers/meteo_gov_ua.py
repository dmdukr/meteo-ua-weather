"""Parser for meteo.gov.ua informer — current weather."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

from ..const import INFORMER_URL, CONDITION_TEXT_MAP, WIND_DIR_DEGREES

_LOGGER = logging.getLogger(__name__)


def _map_condition(text: str) -> str:
    t = text.lower()
    for kw, cond in CONDITION_TEXT_MAP.items():
        if kw in t:
            if cond == "rainy" and "сніг" in t:
                return "snowy-rainy"
            return cond
    return "partlycloudy"


def _parse_informer(body: str) -> dict[str, Any]:
    r: dict[str, Any] = {}

    m = re.search(r"informer-cw-t[^>]*>([^<&]+)", body)
    r["temperature"] = float(m.group(1).replace("+", "").strip()) if m else None

    m = re.search(r"informer-cw-p-d-vp[^>]*>[^>]*>(\d+)", body)
    r["humidity"] = int(m.group(1)) if m else None

    m = re.search(r"informer-cw-p-d-at[^>]*>[^>]*>(\d+)", body)
    r["pressure"] = int(m.group(1)) if m else None

    m = re.search(r"informer-cw-p-d-sv.*?>([\d.]+)\s*<", body, re.DOTALL)
    r["wind_speed"] = float(m.group(1)) if m else None

    m = re.search(r"informer-wd([A-Z]+)", body)
    wc = m.group(1) if m else "N"
    r["wind_bearing"] = WIND_DIR_DEGREES.get(wc, 0)
    r["wind_direction"] = wc

    m = re.search(r'informer-cw-i[^>]*title="([^"]+)"', body)
    ct = m.group(1) if m else "невідомо"
    r["condition_text"] = ct
    r["condition"] = _map_condition(ct)

    return r


async def async_fetch_current(session: aiohttp.ClientSession, station_id: str) -> dict[str, Any]:
    """Fetch current weather from meteo.gov.ua informer."""
    url = INFORMER_URL.format(station=station_id)
    try:
        async with session.get(
            url,
            headers={"User-Agent": "HomeAssistant/MeteoUA"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            body = await resp.text(encoding="utf-8", errors="replace")
            return _parse_informer(body)
    except Exception as exc:
        _LOGGER.error("meteo.gov.ua fetch failed: %s", exc)
        return {
            "temperature": None, "humidity": None, "pressure": None,
            "wind_speed": None, "wind_bearing": 0,
            "condition": "unknown", "condition_text": str(exc),
        }
