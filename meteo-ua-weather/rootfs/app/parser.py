"""Playwright-based parser for meteo.ua pages."""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from playwright.async_api import async_playwright, Page

_LOGGER = logging.getLogger(__name__)
_TZ_KYIV = timezone(timedelta(hours=2))

# Wind direction abbreviations (Ukrainian) to degrees
_WIND_DIR_DEG = {
    "С": 0, "ПнС": 22, "Пн": 0,
    "ПС": 45, "ПнСх": 45,
    "СхПн": 67,
    "Сх": 90, "С": 90,  # "Сх" = East, but "С" alone = North
    "ПдСх": 135, "ЮВ": 135,
    "Пд": 180, "Ю": 180,
    "ПдЗ": 225, "ЮЗ": 225,
    "З": 270, "Зх": 270,
    "ПнЗ": 315, "СЗ": 315,
    "ПнЗх": 315,
    # Russian abbreviations (site sometimes uses them)
    "С": 0, "СВ": 45, "В": 90, "ЮВ": 135,
    "Ю": 180, "ЮЗ": 225, "З": 270, "СЗ": 315,
    # Single-letter Ukrainian
    "П": 180,  # Південь (South)
}

# Condition text to HA condition mapping
_CONDITION_MAP = {
    "ясне небо": "sunny",
    "ясно": "sunny",
    "ясное небо": "sunny",
    "легка хмарність": "partlycloudy",
    "легкая облачность": "partlycloudy",
    "невелика хмарність": "partlycloudy",
    "небольшая облачность": "partlycloudy",
    "помірна хмарність": "cloudy",
    "умеренная облачность": "cloudy",
    "сильна хмарність": "cloudy",
    "облачно с прояснениями": "cloudy",
    "похмура погода": "cloudy",
    "пасмурная погода": "cloudy",
    "похмуро": "cloudy",
    "пасмурно": "cloudy",
    "невеликий дощ": "rainy",
    "небольшой дождь": "rainy",
    "дощ": "rainy",
    "дождь": "rainy",
    "помірний дощ": "rainy",
    "умеренный дождь": "rainy",
    "сильний дощ": "pouring",
    "сильный дождь": "pouring",
    "злива": "pouring",
    "ливень": "pouring",
    "гроза": "lightning",
    "гроза з дощем": "lightning-rainy",
    "гроза с дождем": "lightning-rainy",
    "невеликий сніг": "snowy",
    "небольшой снег": "snowy",
    "сніг": "snowy",
    "снег": "snowy",
    "сильний сніг": "snowy",
    "сильный снег": "snowy",
    "дощ зі снігом": "snowy-rainy",
    "дождь со снегом": "snowy-rainy",
    "мокрий сніг": "snowy-rainy",
    "мокрый снег": "snowy-rainy",
    "туман": "fog",
    "серпанок": "fog",
    "дымка": "fog",
}

_MONTH_NAMES = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
    "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
    "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def _parse_wind_dir(text: str) -> int | None:
    """Convert wind direction text to degrees."""
    text = text.strip()
    if text in _WIND_DIR_DEG:
        return _WIND_DIR_DEG[text]
    return None


def _map_condition(text: str) -> str:
    """Map condition text to HA condition string."""
    return _CONDITION_MAP.get(text.strip().lower(), "cloudy")


def _resolve_date(day: int, month_name: str) -> datetime:
    """Resolve day + month name to full datetime."""
    now = datetime.now(tz=_TZ_KYIV)
    month = _MONTH_NAMES.get(month_name.lower(), now.month)
    year = now.year
    # Handle December→January wrap
    if month < now.month - 1:
        year += 1
    try:
        return datetime(year, month, day, tzinfo=_TZ_KYIV)
    except ValueError:
        return now


async def parse_hourly(page: Page, city_id: str, city_slug: str) -> list[dict[str, Any]]:
    """Parse hourly forecast from meteo.ua /hour page."""
    url = f"https://meteo.ua/ua/{city_id}/{city_slug}/hour"
    _LOGGER.info("Parsing hourly: %s", url)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    # Wait for content to render
    await page.wait_for_timeout(3000)

    body_text = await page.evaluate("() => document.body.innerText")

    lines = body_text.split("\n")
    result = []
    current_date = None  # datetime object for current day section

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Date header: "15 березня" or "16 марта"
        date_match = re.match(r"^(\d{1,2})\s+(\S+)$", line)
        if date_match:
            day = int(date_match.group(1))
            month_name = date_match.group(2)
            if month_name.lower() in _MONTH_NAMES:
                current_date = _resolve_date(day, month_name)
            continue

        # Data row: "13:00  +11 ° ясне небо  С  5.1 м/c  26%  766 мм рт. ст."
        row_match = re.match(
            r"(\d{1,2}):(\d{2})\s+([+-]?\d+)\s*°\s*(.+?)\t"
            r"(\S+)\s+([\d.]+)\s*м/[cс]\s+(\d+)%\s+(\d+)\s*мм",
            line,
        )
        if row_match and current_date:
            hour = int(row_match.group(1))
            minute = int(row_match.group(2))
            temp = int(row_match.group(3))
            condition_text = row_match.group(4).strip()
            wind_dir_text = row_match.group(5)
            wind_speed = float(row_match.group(6))
            humidity = int(row_match.group(7))
            pressure = int(row_match.group(8))

            dt = current_date.replace(hour=hour, minute=minute, second=0)

            result.append({
                "datetime": dt.isoformat(),
                "temperature": temp,
                "condition": _map_condition(condition_text),
                "condition_text": condition_text,
                "humidity": humidity,
                "pressure": pressure,
                "wind_speed": wind_speed,
                "wind_bearing": _parse_wind_dir(wind_dir_text),
                "wind_direction": wind_dir_text,
            })

    _LOGGER.info("Parsed %d hourly entries for %s", len(result), city_slug)
    return result


async def parse_current(page: Page, city_id: str, city_slug: str) -> dict[str, Any]:
    """Parse current weather from meteo.ua main city page."""
    url = f"https://meteo.ua/ua/{city_id}/{city_slug}"
    _LOGGER.info("Parsing current: %s", url)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    body_text = await page.evaluate("() => document.body.innerText")

    result: dict[str, Any] = {}

    # Try to extract current temperature: "+11°" pattern
    temp_match = re.search(r"([+-]?\d+)\s*°", body_text)
    if temp_match:
        result["temperature"] = int(temp_match.group(1))

    # Extract condition, humidity, pressure, wind from page text
    # Pattern depends on page layout - extract what we can
    lines = body_text.split("\n")
    for line in lines:
        line = line.strip()
        hum_match = re.search(r"(\d+)\s*%", line)
        if hum_match and "humidity" not in result and "вологість" in line.lower():
            result["humidity"] = int(hum_match.group(1))

        pres_match = re.search(r"(\d{3,4})\s*мм", line)
        if pres_match and "pressure" not in result:
            result["pressure"] = int(pres_match.group(1))

        wind_match = re.search(r"([\d.]+)\s*м/[cс]", line)
        if wind_match and "wind_speed" not in result:
            result["wind_speed"] = float(wind_match.group(1))

    # If current page fails (404), use first entry from hourly as fallback
    if "temperature" not in result:
        _LOGGER.warning("Current page parse incomplete for %s, will use hourly fallback", city_slug)

    return result


async def parse_daily(page: "Page", city_id: str, city_slug: str) -> list[dict[str, Any]]:
    """Parse 30-day forecast from meteo.ua /month page via headless browser."""
    url = f"https://meteo.ua/ua/{city_id}/{city_slug}/month"
    _LOGGER.info("Parsing daily (browser): %s", url)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    # Get rendered DOM text for min..max temps
    body_text = await page.evaluate("() => document.body.innerText")
    temp_ranges = re.findall(r"([+-]?\d+)\s*°\s*\.\.\s*([+-]?\d+)\s*°", body_text)
    _LOGGER.info("Found %d temp ranges in DOM for %s", len(temp_ranges), city_slug)

    # Also get the page HTML for data-key parsing (icons, wind, conditions)
    html = await page.content()
    import aiohttp  # noqa: keep for type hints

    # html already fetched via page.content() above

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

    today = datetime.now(tz=_TZ_KYIV).replace(hour=12, minute=0, second=0, microsecond=0)
    forecast = []
    for i in range(min(30, len(temps))):
        temp_str = temps[i].strip()
        temp_match = re.search(r"[+-]?\d+", temp_str)
        temp = int(temp_match.group()) if temp_match else None

        wind_str = winds[i].strip() if i < len(winds) else ""
        wind_match = re.search(r"[\d.]+", wind_str)
        wind_speed = float(wind_match.group()) if wind_match else None

        condition_text = infos[i].strip() if i < len(infos) else ""
        dt = today + timedelta(days=i)

        entry: dict[str, Any] = {
            "datetime": dt.isoformat(),
            "temperature": temp,
            "condition": _map_condition(condition_text),
            "condition_text": condition_text,
            "wind_speed": wind_speed,
        }

        # Use DOM-rendered min..max if available
        if i < len(temp_ranges):
            lo, hi = int(temp_ranges[i][0]), int(temp_ranges[i][1])
            entry["templow"] = lo
            entry["temperature"] = hi

        forecast.append(entry)

    _LOGGER.info("Parsed %d daily entries for %s", len(forecast), city_slug)
    return forecast


async def run_parse_session(cities: list[dict], parse_types: list[str]) -> dict[str, dict]:
    """Run a Chromium session to parse requested data for all cities.

    parse_types: subset of ["current", "hourly", "daily"]
    Returns: {"{city_id}/{city_slug}": {"current": {...}, "hourly": [...], "daily": [...]}}
    """
    results: dict[str, dict] = {}

    # All parse types now use headless browser
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()

        for city in cities:
            cid = city["city_id"]
            cslug = city["city_slug"]
            key = f"{cid}/{cslug}"
            results.setdefault(key, {})

            try:
                if "hourly" in parse_types:
                    results[key]["hourly"] = await parse_hourly(page, cid, cslug)

                if "current" in parse_types:
                    data = await parse_current(page, cid, cslug)
                    if "temperature" not in data and results[key].get("hourly"):
                        h0 = results[key]["hourly"][0]
                        data = {
                            "temperature": h0["temperature"],
                            "condition": h0["condition"],
                            "condition_text": h0.get("condition_text", ""),
                            "humidity": h0.get("humidity"),
                            "pressure": h0.get("pressure"),
                            "wind_speed": h0.get("wind_speed"),
                            "wind_bearing": h0.get("wind_bearing"),
                        }
                    results[key]["current"] = data

                if "daily" in parse_types:
                    results[key]["daily"] = await parse_daily(page, cid, cslug)

            except Exception as exc:
                _LOGGER.error("Parse error for %s: %s", key, exc)

        await browser.close()

    return results
