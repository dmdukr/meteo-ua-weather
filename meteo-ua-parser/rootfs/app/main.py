"""Meteo UA Parser — HTTP API server with scheduled Chromium parsing."""
import asyncio
import json
import logging
import os
import random
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
OPTIONS_FILE = Path("/data/options.json")

_LOGGER = logging.getLogger("meteo_ua_parser")


def load_options() -> dict:
    """Load add-on options."""
    if OPTIONS_FILE.exists():
        return json.loads(OPTIONS_FILE.read_text())
    # Fallback for development
    return {
        "cities": [{"city_id": "34", "city_slug": "kiev"}],
        "log_level": "info",
    }


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
    options = load_options()
    cities = options.get("cities", [])

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


# --- Scheduler ---

async def scheduler(app: web.Application) -> None:
    """Background scheduler — runs cron-like tasks."""
    options = load_options()
    cities = options.get("cities", [])
    schedule = get_schedule()

    _LOGGER.info("Scheduler started. Cities: %s", [c["city_slug"] for c in cities])

    # Initial parse on startup
    _LOGGER.info("Running initial parse...")
    try:
        results = await run_parse_session(cities, ["current", "hourly", "daily"])
        cache = {"data": results}
        now = datetime.now(timezone.utc).isoformat()
        cache["last_update"] = {"current": now, "hourly": now, "daily": now}
        save_cache(cache)
        _LOGGER.info("Initial parse complete: %d cities", len(results))
    except Exception as exc:
        _LOGGER.error("Initial parse failed: %s", exc)

    while True:
        try:
            now = datetime.now(timezone(timedelta(hours=2)))  # Kyiv time
            current_minute = now.minute
            current_hour = now.hour

            # Wait until next minute boundary
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            wait_seconds = (next_minute - now).total_seconds()
            await asyncio.sleep(wait_seconds + 1)  # +1 to be safely in the new minute

            now = datetime.now(timezone(timedelta(hours=2)))
            minute = now.minute
            hour = now.hour

            parse_types = []

            # Check which schedules match this minute
            if minute == schedule["current_minute"]:
                parse_types.append("current")

            if minute == schedule["hourly_minute"] and hour % 3 == 0:
                parse_types.append("hourly")

            if minute == schedule["daily_minute"] and hour % 6 == 0:
                parse_types.append("daily")

            if not parse_types:
                continue

            # Combine into one Chromium session
            _LOGGER.info("Scheduled parse: %s at %02d:%02d", parse_types, hour, minute)
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
    return web.json_response({"status": "ok", "message": "Integration and card removed"})


def main() -> None:
    options = load_options()
    log_level = getattr(logging, options.get("log_level", "info").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    # Install/update integration and card on startup
    _LOGGER.info("Checking integration and card installation...")
    needs_restart = install_all()
    if needs_restart:
        _LOGGER.info("Integration/card installed or updated. HA restart may be needed.")

    app = web.Application()
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/current/{city_id}/{city_slug}", handle_current)
    app.router.add_get("/api/hourly/{city_id}/{city_slug}", handle_hourly)
    app.router.add_get("/api/daily/{city_id}/{city_slug}", handle_daily)
    app.router.add_post("/api/refresh", handle_refresh)
    app.router.add_post("/api/uninstall", handle_uninstall)

    app.on_startup.append(start_scheduler)
    app.on_cleanup.append(stop_scheduler)

    _LOGGER.info("Meteo UA Parser starting on port 5581")
    web.run_app(app, host="0.0.0.0", port=5581, print=None)


if __name__ == "__main__":
    main()
