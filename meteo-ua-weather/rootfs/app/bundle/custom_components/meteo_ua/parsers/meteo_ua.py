"""Parser for meteo.ua — 30-day monthly forecast (HTML scraping)."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

from ..const import MONTHLY_URL, ICON_TO_HA_CONDITION

_LOGGER = logging.getLogger(__name__)

# ── Localization tables ─────────────────────────────────────────────────────
# With /ua/ prefix meteo.ua returns Ukrainian content natively.
# For non-Ukrainian HAOS we translate UK → EN.

_MONTHS_UK_EN = {
    "січня": "January", "лютого": "February", "березня": "March",
    "квітня": "April", "травня": "May", "червня": "June",
    "липня": "July", "серпня": "August", "вересня": "September",
    "жовтня": "October", "листопада": "November", "грудня": "December",
}

_CONDITIONS_UK_EN = {
    "ясне небо": "clear sky",
    "ясно": "clear",
    "легка хмарність": "partly cloudy",
    "невелика хмарність": "partly cloudy",
    "розсіяні хмари": "scattered clouds",
    "хмарно з проясненнями": "mostly cloudy",
    "похмура погода": "overcast",
    "похмуро": "overcast",
    "невеликий дощ": "light rain",
    "дощ": "rain",
    "помірний дощ": "moderate rain",
    "сильний дощ": "heavy rain",
    "злива": "downpour",
    "гроза": "thunderstorm",
    "гроза з дощем": "thunderstorm with rain",
    "гроза з сильним дощем": "thunderstorm with heavy rain",
    "невеликий сніг": "light snow",
    "сніг": "snow",
    "сильний сніг": "heavy snow",
    "снігопад": "snowfall",
    "дощ зі снігом": "rain and snow",
    "мокрий сніг": "sleet",
    "туман": "fog",
    "серпанок": "haze",
}


def _resolve_locale(lang: str) -> str:
    """uk/ru → 'uk' (pass-through), everything else → 'en' (translate)."""
    return "uk" if lang in ("uk", "ru") else "en"


def _localize_date(text: str, locale: str) -> str:
    if locale == "uk":
        return text
    result = text
    for uk, en in _MONTHS_UK_EN.items():
        result = result.replace(uk, en)
    return result


def _localize_condition(text: str, locale: str) -> str:
    if locale == "uk":
        return text
    lower = text.strip().lower()
    return _CONDITIONS_UK_EN.get(lower, text)


def _localize_wind(text: str, locale: str) -> str:
    if locale == "en":
        return text.replace("м/с", "m/s")
    return text


# ── Icon mapping ────────────────────────────────────────────────────────────

def _map_icon(raw: str) -> str:
    if not raw:
        return "cloudy"
    for k, v in ICON_TO_HA_CONDITION.items():
        if k in raw:
            return v
    return "cloudy"


# ── HTML parser ─────────────────────────────────────────────────────────────

def _parse_temp_value(s: str) -> float | None:
    """Extract numeric temperature from string like '+6°' or '−2°'."""
    if not s:
        return None
    m = re.search(r"[+-]?\d+", s.replace("\u2212", "-").replace("−", "-"))
    return float(m.group()) if m else None


def _parse_monthly(html: str, locale: str = "uk") -> list[dict[str, Any]]:
    temps = re.findall(r'data-key="temperature">([^<]+)', html)
    infos = re.findall(r'data-key="info">([^<]+)', html)
    winds_all = re.findall(r'data-key="wind">([^<]+)', html)
    winds = winds_all[::2] if winds_all else []
    captions = re.findall(r'data-key="caption"[^>]*>([^<]+)', html)

    # Parse period temperatures: 4 per day (Ранок, День, Вечір, Ніч)
    period_temps = re.findall(r'weather-detail__main-period-temp[^>]*>([^<]+)', html)
    day_temps: list[float | None] = []
    night_temps: list[float | None] = []
    for i in range(0, len(period_temps), 4):
        chunk = period_temps[i:i + 4]
        day_temps.append(_parse_temp_value(chunk[1]) if len(chunk) > 1 else None)    # День
        night_temps.append(_parse_temp_value(chunk[3]) if len(chunk) > 3 else None)  # Ніч

    icons_raw = re.findall(
        r'weather-detail__main-icon[^>]*>.*?(?:href|xlink:href)="[^#]*#weather-([^"]+)"',
        html, re.DOTALL,
    )
    if len(icons_raw) < len(temps):
        icons_raw = re.findall(r'data-src="[^"]*sprite\.svg#weather-([^"]+)"', html)
        deduped, prev = [], ""
        for ic in icons_raw:
            if ic.startswith("detail"):
                continue
            if ic != prev:
                deduped.append(ic)
                prev = ic
            if len(deduped) >= 30:
                break
        icons_raw = deduped

    forecast = []
    for i in range(min(30, len(temps))):
        date_str = ""
        if i < len(captions):
            m = re.search(r"(\d+\s+\S+)", captions[i])
            if m:
                date_str = m.group(1).strip()
        icon_raw = icons_raw[i] if i < len(icons_raw) else ""
        entry: dict[str, Any] = {
            "day": i + 1,
            "date": _localize_date(date_str, locale),
            "temp": temps[i].strip(),
            "condition": _localize_condition(infos[i].strip(), locale) if i < len(infos) else "",
            "ha_condition": _map_icon(icon_raw),
            "wind": _localize_wind(winds[i].strip(), locale) if i < len(winds) else "",
            "icon": icon_raw,
        }
        if i < len(day_temps) and day_temps[i] is not None:
            entry["temp_day"] = day_temps[i]
        if i < len(night_temps) and night_temps[i] is not None:
            entry["temp_night"] = night_temps[i]
        forecast.append(entry)
    return forecast


async def async_fetch_monthly(
    session: aiohttp.ClientSession, city_id: str, city_slug: str,
    lang: str = "uk",
) -> dict[str, Any]:
    """Fetch 30-day forecast from meteo.ua."""
    locale = _resolve_locale(lang)
    url = MONTHLY_URL.format(city_id=city_id, city_slug=city_slug)
    try:
        async with session.get(
            url,
            headers={"User-Agent": "HomeAssistant/MeteoUA"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            resp.raise_for_status()
            html = await resp.text(encoding="utf-8", errors="replace")
            fc = _parse_monthly(html, locale)
            return {"forecast": fc, "days": len(fc), "city": city_slug}
    except Exception as exc:
        _LOGGER.error("meteo.ua fetch failed: %s", exc)
        return {"forecast": [], "days": 0, "city": city_slug, "error": str(exc)}
