"""Meteo UA Parser — HTTP API server with scheduled Chromium parsing."""
import asyncio
import json
import logging
import os
import random
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from aiohttp import web

from parser import run_parse_session
from installer import install_all, uninstall_all

# --- Config ---
DATA_DIR = Path("/data")
CACHE_FILE = DATA_DIR / "cache.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
CITIES_FILE = DATA_DIR / "cities.json"
OPTIONS_FILE = Path("/data/options.json")

_LOGGER = logging.getLogger("meteo_ua_parser")


def load_options() -> dict:
    """Load add-on options."""
    if OPTIONS_FILE.exists():
        return json.loads(OPTIONS_FILE.read_text())
    return {"log_level": "info"}


def load_cities() -> list[dict]:
    """Load registered cities from /data/cities.json."""
    if CITIES_FILE.exists():
        try:
            return json.loads(CITIES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_cities(cities: list[dict]) -> None:
    """Save registered cities."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CITIES_FILE.write_text(json.dumps(cities, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache() -> dict[str, Any]:
    """Load cached weather data."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(data: dict[str, Any]) -> None:
    """Save weather data to cache."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_schedule() -> dict[str, int]:
    """Get or create randomized schedule minutes."""
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    schedule = {
        "current_minute": random.randint(0, 59),
        "hourly_minute": random.randint(0, 59),
        "daily_minute": random.randint(0, 59),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(schedule, indent=2))
    _LOGGER.info(
        "Generated schedule: current=:%02d, hourly=:%02d, daily=:%02d",
        schedule["current_minute"],
        schedule["hourly_minute"],
        schedule["daily_minute"],
    )
    return schedule


# --- HTTP handlers ---

async def handle_health(request: web.Request) -> web.Response:
    cache = load_cache()
    return web.json_response({
        "status": "ok",
        "cities": list(cache.get("data", {}).keys()),
        "last_update": cache.get("last_update", {}),
    })


async def handle_hourly(request: web.Request) -> web.Response:
    city_id = request.match_info["city_id"]
    city_slug = request.match_info["city_slug"]
    key = f"{city_id}/{city_slug}"

    cache = load_cache()
    city_data = cache.get("data", {}).get(key, {})
    hourly = city_data.get("hourly", [])

    return web.json_response(hourly)


async def handle_daily(request: web.Request) -> web.Response:
    city_id = request.match_info["city_id"]
    city_slug = request.match_info["city_slug"]
    key = f"{city_id}/{city_slug}"

    cache = load_cache()
    city_data = cache.get("data", {}).get(key, {})
    daily = city_data.get("daily", [])

    return web.json_response(daily)


async def handle_current(request: web.Request) -> web.Response:
    city_id = request.match_info["city_id"]
    city_slug = request.match_info["city_slug"]
    key = f"{city_id}/{city_slug}"

    cache = load_cache()
    city_data = cache.get("data", {}).get(key, {})
    current = city_data.get("current", {})

    return web.json_response(current)


async def handle_refresh(request: web.Request) -> web.Response:
    """Manual refresh trigger."""
    cities = load_cities()

    _LOGGER.info("Manual refresh triggered for %d cities", len(cities))
    try:
        results = await run_parse_session(cities, ["current", "hourly", "daily"])
        cache = load_cache()
        cache.setdefault("data", {}).update(results)
        now = datetime.now(timezone.utc).isoformat()
        cache["last_update"] = {"current": now, "hourly": now, "daily": now}
        save_cache(cache)
        return web.json_response({"status": "ok", "cities": list(results.keys())})
    except Exception as exc:
        _LOGGER.error("Refresh failed: %s", exc)
        return web.json_response({"status": "error", "error": str(exc)}, status=500)


async def handle_register_city(request: web.Request) -> web.Response:
    """Register a city for parsing. Called by integration on setup."""
    data = await request.json()
    city_id = str(data.get("city_id", ""))
    city_slug = str(data.get("city_slug", ""))

    if not city_id or not city_slug:
        return web.json_response({"error": "city_id and city_slug required"}, status=400)

    cities = load_cities()
    # Check if already registered
    if any(c["city_id"] == city_id and c["city_slug"] == city_slug for c in cities):
        return web.json_response({"status": "ok", "message": "already registered"})

    cities.append({"city_id": city_id, "city_slug": city_slug})
    save_cities(cities)
    _LOGGER.info("City registered: %s/%s (total: %d)", city_id, city_slug, len(cities))

    # Parse immediately for the new city
    try:
        results = await run_parse_session(
            [{"city_id": city_id, "city_slug": city_slug}],
            ["current", "hourly", "daily"],
        )
        cache = load_cache()
        cache.setdefault("data", {}).update(results)
        now = datetime.now(timezone.utc).isoformat()
        cache.setdefault("last_update", {}).update({"current": now, "hourly": now, "daily": now})
        save_cache(cache)
    except Exception as exc:
        _LOGGER.warning("Initial parse for %s/%s failed: %s", city_id, city_slug, exc)

    return web.json_response({"status": "ok", "cities": len(cities)})


async def handle_unregister_city(request: web.Request) -> web.Response:
    """Unregister a city. Called by integration on removal."""
    data = await request.json()
    city_id = str(data.get("city_id", ""))
    city_slug = str(data.get("city_slug", ""))

    cities = load_cities()
    cities = [c for c in cities if not (c["city_id"] == city_id and c["city_slug"] == city_slug)]
    save_cities(cities)

    # Remove cached data for this city
    key = f"{city_id}/{city_slug}"
    cache = load_cache()
    cache.get("data", {}).pop(key, None)
    save_cache(cache)

    _LOGGER.info("City unregistered: %s/%s (remaining: %d)", city_id, city_slug, len(cities))
    return web.json_response({"status": "ok", "cities": len(cities)})


async def handle_list_cities(request: web.Request) -> web.Response:
    """List registered cities."""
    return web.json_response(load_cities())


# --- Scheduler ---

async def scheduler(app: web.Application) -> None:
    """Background scheduler — runs cron-like tasks."""
    schedule = get_schedule()

    # Initial parse on startup
    cities = load_cities()
    if cities:
        _LOGGER.info("Running initial parse for %d cities...", len(cities))
        try:
            results = await run_parse_session(cities, ["current", "hourly", "daily"])
            cache = {"data": results}
            now = datetime.now(timezone.utc).isoformat()
            cache["last_update"] = {"current": now, "hourly": now, "daily": now}
            save_cache(cache)
            _LOGGER.info("Initial parse complete: %d cities", len(results))
        except Exception as exc:
            _LOGGER.error("Initial parse failed: %s", exc)
    else:
        _LOGGER.warning("No cities registered — waiting for integration to register cities")

    while True:
        try:
            now = datetime.now(timezone(timedelta(hours=2)))  # Kyiv time

            # Wait until next minute boundary
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            wait_seconds = (next_minute - now).total_seconds()
            await asyncio.sleep(wait_seconds + 1)

            now = datetime.now(timezone(timedelta(hours=2)))
            minute = now.minute
            hour = now.hour

            parse_types = []

            if minute == schedule["current_minute"]:
                parse_types.append("current")

            if minute == schedule["hourly_minute"] and hour % 3 == 0:
                parse_types.append("hourly")

            if minute == schedule["daily_minute"] and hour % 6 == 0:
                parse_types.append("daily")

            if not parse_types:
                continue

            # Re-read cities each time (integration may have added/removed)
            cities = load_cities()
            if not cities:
                continue

            _LOGGER.info("Scheduled parse: %s at %02d:%02d (%d cities)", parse_types, hour, minute, len(cities))
            results = await run_parse_session(cities, parse_types)

            cache = load_cache()
            now_iso = datetime.now(timezone.utc).isoformat()
            for key, data in results.items():
                cache.setdefault("data", {}).setdefault(key, {}).update(data)
            for pt in parse_types:
                cache.setdefault("last_update", {})[pt] = now_iso
            save_cache(cache)

            _LOGGER.info("Scheduled parse complete: %s", parse_types)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            _LOGGER.error("Scheduler error: %s", exc)
            await asyncio.sleep(60)


async def start_scheduler(app: web.Application) -> None:
    app["scheduler_task"] = asyncio.create_task(scheduler(app))


async def stop_scheduler(app: web.Application) -> None:
    task = app.get("scheduler_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# --- Main ---

async def handle_uninstall(request: web.Request) -> web.Response:
    """Remove integration and card files."""
    _LOGGER.info("Uninstall requested — removing integration and card")
    uninstall_all()
    _notify_restart(
        "Інтеграцію Meteo UA Weather та карточку прогнозу видалено. "
        "**[Перезавантажте Home Assistant](/developer-tools/yaml)** для завершення.\n\n"
        "Meteo UA Weather integration and forecast card removed. "
        "**[Restart Home Assistant](/developer-tools/yaml)** to complete removal.",
        notification_id="meteo_ua_removed",
    )
    return web.json_response({"status": "ok", "message": "Integration and card removed"})


async def handle_test_notify(request: web.Request) -> web.Response:
    """Test notification delivery."""
    _LOGGER.info("Test notification requested")
    _notify_restart("Тестове повідомлення від Meteo UA Parser. / Test notification from Meteo UA Parser.")
    return web.json_response({"status": "ok", "message": "Test notification sent"})


def _notify_restart(message: str, notification_id: str = "meteo_ua_restart_required") -> None:
    """Send persistent notification to HA via Supervisor API."""
    import urllib.request

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not supervisor_token:
        _LOGGER.warning("No SUPERVISOR_TOKEN — cannot notify HA")
        return

    headers = {
        "Authorization": f"Bearer {supervisor_token}",
        "Content-Type": "application/json",
    }

    try:
        data = json.dumps({
            "title": "Meteo UA Weather",
            "message": message,
            "notification_id": notification_id,
        }).encode()
        req = urllib.request.Request(
            "http://supervisor/core/api/services/persistent_notification/create",
            data=data, headers=headers, method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        _LOGGER.info("Notification sent to HA (id: %s)", notification_id)
    except Exception as exc:
        _LOGGER.warning("Failed to send notification: %s", exc)




def main() -> None:
    options = load_options()
    log_level = getattr(logging, options.get("log_level", "info").upper(), logging.INFO)

    class _ColorFormatter(logging.Formatter):
        _TIME_COLORS = {
            logging.DEBUG:    "\033[32m",   # green
            logging.INFO:     "\033[32m",   # green
            logging.WARNING:  "\033[33m",   # yellow
            logging.ERROR:    "\033[31m",   # red
            logging.CRITICAL: "\033[31m",   # red
        }
        _RESET  = "\033[0m"
        _WHITE  = "\033[97m"
        _CYAN   = "\033[96m"

        def format(self, record):
            time_color = self._TIME_COLORS.get(record.levelno, "\033[32m")
            ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
            ms = int(record.msecs)
            level = record.levelname
            name = record.name
            msg = record.getMessage()
            return (
                f"{time_color}{ts},{ms:03d}{self._RESET} "
                f"{time_color}[{name}] {level}{self._RESET}: "
                f"{self._WHITE}{msg}{self._RESET}"
            )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ColorFormatter())
    logging.basicConfig(level=log_level, handlers=[handler])


    # Log versions
    addon_version = os.environ.get("BUILD_VERSION", "?")
    integration_version = "?"
    card_version = "?"
    try:
        import json as _json
        manifest = _json.loads(Path("/app/bundle/custom_components/meteo_ua/manifest.json").read_text())
        integration_version = manifest.get("version", "?")
    except Exception:
        pass
    try:
        # Card version is embedded in the JS bundle
        card_js = Path("/app/bundle/custom_components/meteo_ua/frontend/atmospheric-weather-card.js")
        if card_js.exists():
            import re
            m = re.search(r'"version":"([^"]+)"', card_js.read_text(encoding="utf-8"))
            if m:
                card_version = m.group(1)
    except Exception:
        pass
    _LOGGER.info(
        "Meteo UA Weather — addon v%s, integration v%s, card v%s",
        addon_version, integration_version, card_version,
    )

    # Install/update integration and card on startup
    _LOGGER.info("Checking integration and card installation...")
    changes = install_all()

    if changes.get("integration") or changes.get("new_install"):
        _LOGGER.info("Integration changed — notifying user to restart HA")
        _notify_restart(
            "Інтеграцію Meteo UA Weather оновлено. "
            "**[Перезавантажте Home Assistant](/developer-tools/yaml)** для активації змін.\n\n"
            "Meteo UA Weather integration updated. "
            "**[Restart Home Assistant](/developer-tools/yaml)** to activate changes.",
            notification_id="meteo_ua_restart_required",
        )
    elif changes.get("card"):
        _LOGGER.info("Card JS changed — notifying user to refresh browser")
        _notify_restart(
            "Карточку Meteo UA Weather оновлено. "
            "Оновіть сторінку у браузері (**Ctrl+Shift+R**).\n\n"
            "Meteo UA Weather card updated. "
            "Refresh your browser (**Ctrl+Shift+R**).",
            notification_id="meteo_ua_card_updated",
        )
    else:
        _LOGGER.info("Integration and card up to date — no action needed")

    app = web.Application()
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/current/{city_id}/{city_slug}", handle_current)
    app.router.add_get("/api/hourly/{city_id}/{city_slug}", handle_hourly)
    app.router.add_get("/api/daily/{city_id}/{city_slug}", handle_daily)
    app.router.add_post("/api/refresh", handle_refresh)
    app.router.add_post("/api/uninstall", handle_uninstall)
    app.router.add_post("/api/test-notify", handle_test_notify)
    app.router.add_post("/api/cities/register", handle_register_city)
    app.router.add_post("/api/cities/unregister", handle_unregister_city)
    app.router.add_get("/api/cities", handle_list_cities)

    app.on_startup.append(start_scheduler)
    app.on_cleanup.append(stop_scheduler)

    _LOGGER.info("Meteo UA Parser starting on port 5581")
    web.run_app(app, host="0.0.0.0", port=5581, print=None)


if __name__ == "__main__":
    main()
