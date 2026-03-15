"""Parser for meteo.ua — 30-day monthly forecast (HTML scraping)."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

from ..const import MONTHLY_URL, ICON_TO_HA_CONDITION

_LOGGER = logging.getLogger(__name__)

# ── Localization tables ─────────────────────────────────────────────────────
# meteo.ua always returns Russian. We translate to Ukrainian or English
# depending on HAOS language. Russian/Ukrainian → uk, everything else → en.

_MONTHS_RU_UK = {
    "января": "січня", "февраля": "лютого", "марта": "березня",
    "апреля": "квітня", "мая": "травня", "июня": "червня",
    "июля": "липня", "августа": "серпня", "сентября": "вересня",
    "октября": "жовтня", "ноября": "листопада", "декабря": "грудня",
}

_MONTHS_RU_EN = {
    "января": "January", "февраля": "February", "марта": "March",
    "апреля": "April", "мая": "May", "июня": "June",
    "июля": "July", "августа": "August", "сентября": "September",
    "октября": "October", "ноября": "November", "декабря": "December",
}

_CONDITIONS_RU_UK = {
    "ясное небо": "ясне небо",
    "ясно": "ясно",
    "легкая облачность": "легка хмарність",
    "небольшая облачность": "невелика хмарність",
    "рассеянные облака": "розсіяні хмари",
    "облачно с прояснениями": "хмарно з проясненнями",
    "пасмурная погода": "похмура погода",
    "пасмурно": "похмуро",
    "небольшой дождь": "невеликий дощ",
    "дождь": "дощ",
    "умеренный дождь": "помірний дощ",
    "сильный дождь": "сильний дощ",
    "ливень": "злива",
    "гроза": "гроза",
    "гроза с дождем": "гроза з дощем",
    "гроза с сильным дождем": "гроза з сильним дощем",
    "небольшой снег": "невеликий сніг",
    "снег": "сніг",
    "сильный снег": "сильний сніг",
    "снегопад": "снігопад",
    "дождь со снегом": "дощ зі снігом",
    "мокрый снег": "мокрий сніг",
    "туман": "туман",
    "дымка": "серпанок",
}

_CONDITIONS_RU_EN = {
    "ясное небо": "clear sky",
    "ясно": "clear",
    "легкая облачность": "partly cloudy",
    "небольшая облачность": "partly cloudy",
    "рассеянные облака": "scattered clouds",
    "облачно с прояснениями": "mostly cloudy",
    "пасмурная погода": "overcast",
    "пасмурно": "overcast",
    "небольшой дождь": "light rain",
    "дождь": "rain",
    "умеренный дождь": "moderate rain",
    "сильный дождь": "heavy rain",
    "ливень": "downpour",
    "гроза": "thunderstorm",
    "гроза с дождем": "thunderstorm with rain",
    "гроза с сильным дождем": "thunderstorm with heavy rain",
    "небольшой снег": "light snow",
    "снег": "snow",
    "сильный снег": "heavy snow",
    "снегопад": "snowfall",
    "дождь со снегом": "rain and snow",
    "мокрый снег": "sleet",
    "туман": "fog",
    "дымка": "haze",
}

_WIND_UNIT = {"uk": "м/с", "en": "m/s"}


def _resolve_locale(lang: str) -> str:
    """ru/uk → 'uk', everything else → 'en'."""
    return "uk" if lang in ("uk", "ru") else "en"


def _localize_date(text: str, locale: str) -> str:
    table = _MONTHS_RU_UK if locale == "uk" else _MONTHS_RU_EN
    result = text
    for ru, loc in table.items():
        result = result.replace(ru, loc)
    return result


def _localize_condition(text: str, locale: str) -> str:
    table = _CONDITIONS_RU_UK if locale == "uk" else _CONDITIONS_RU_EN
    lower = text.strip().lower()
    return table.get(lower, _localize_date(text, locale))


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

def _parse_monthly(html: str, locale: str = "uk") -> list[dict[str, Any]]:
    temps = re.findall(r'data-key="temperature">([^<]+)', html)
    infos = re.findall(r'data-key="info">([^<]+)', html)
    winds_all = re.findall(r'data-key="wind">([^<]+)', html)
    winds = winds_all[::2] if winds_all else []
    captions = re.findall(r'data-key="caption"[^>]*>([^<]+)', html)

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
        forecast.append({
            "day": i + 1,
            "date": _localize_date(date_str, locale),
            "temp": temps[i].strip(),
            "condition": _localize_condition(infos[i].strip(), locale) if i < len(infos) else "",
            "ha_condition": _map_icon(icon_raw),
            "wind": _localize_wind(winds[i].strip(), locale) if i < len(winds) else "",
            "icon": icon_raw,
        })
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
