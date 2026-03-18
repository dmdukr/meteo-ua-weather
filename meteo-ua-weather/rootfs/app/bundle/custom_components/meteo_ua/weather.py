"""Weather platform for Meteo UA."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CITY_NAME, CONF_CITY_SLUG
from .coordinator import MeteoUaCoordinator

_UA_TZ = timezone(timedelta(hours=2))

# All HA weather conditions for icon test
_ALL_CONDITIONS = [
    "sunny",
    "clear-night",
    "partlycloudy",
    "cloudy",
    "rainy",
    "pouring",
    "lightning",
    "lightning-rainy",
    "snowy",
    "snowy-rainy",
    "fog",
    "hail",
    "windy",
    "windy-variant",
    "exceptional",
]

# Set to True to test all icons (each day = different condition)
_TEST_ICONS = True


def _parse_temp(temp_str: str) -> float | None:
    if not temp_str:
        return None
    m = re.search(r"[+-]?\d+", temp_str.replace("\u2212", "-"))
    return float(m.group()) if m else None


def _parse_wind_speed(wind_str: str) -> float | None:
    if not wind_str:
        return None
    m = re.search(r"[\d.]+", wind_str)
    return float(m.group()) if m else None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MeteoUaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoUaWeather(coordinator, entry)])


class MeteoUaWeather(CoordinatorEntity[MeteoUaCoordinator], WeatherEntity):
    """Current weather + 30-day daily forecast."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.MMHG
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator: MeteoUaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"meteo_ua_weather_{entry.data[CONF_CITY_SLUG]}"
        self._attr_name = f"Meteo UA {entry.data[CONF_CITY_NAME]}"
        self._attr_attribution = "meteo.ua"

    @property
    def condition(self) -> str | None:
        return self.coordinator.data.get("current", {}).get("condition")

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("temperature")

    @property
    def humidity(self) -> int | None:
        return self.coordinator.data.get("current", {}).get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("pressure")

    @property
    def native_wind_speed(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("wind_speed")

    @property
    def wind_bearing(self) -> int | None:
        return self.coordinator.data.get("current", {}).get("wind_bearing")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cur = self.coordinator.data.get("current", {})
        monthly = self.coordinator.data.get("monthly", {})
        return {
            "condition_text": cur.get("condition_text", ""),
            "wind_direction": cur.get("wind_direction", ""),
            "forecast": monthly.get("forecast", []),
            "forecast_days": monthly.get("days", 0),
            "forecast_city": monthly.get("city", ""),
        }

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return 30-day daily forecast in HA standard format."""
        now = datetime.now(_UA_TZ)

        if _TEST_ICONS:
            return self._test_forecast(now)

        return self._real_forecast(now)

    def _real_forecast(self, now: datetime) -> list[Forecast]:
        monthly = self.coordinator.data.get("monthly", {})
        raw = monthly.get("forecast", [])
        result: list[Forecast] = []
        for i, day in enumerate(raw):
            dt = now + timedelta(days=i)
            result.append(
                Forecast(
                    datetime=dt.strftime("%Y-%m-%dT00:00:00+02:00"),
                    condition=day.get("ha_condition", "cloudy"),
                    native_temperature=_parse_temp(day.get("temp", "")),
                    native_wind_speed=_parse_wind_speed(day.get("wind", "")),
                )
            )
        return result

    def _test_forecast(self, now: datetime) -> list[Forecast]:
        """Generate 30 days with cycling through all HA conditions."""
        result: list[Forecast] = []
        for i in range(30):
            dt = now + timedelta(days=i)
            cond = _ALL_CONDITIONS[i % len(_ALL_CONDITIONS)]
            temp = -10 + i * 1.5  # gradient from -10 to +33
            result.append(
                Forecast(
                    datetime=dt.strftime("%Y-%m-%dT00:00:00+02:00"),
                    condition=cond,
                    native_temperature=round(temp, 1),
                    native_wind_speed=round(1.0 + i * 0.3, 1),
                )
            )
        return result
