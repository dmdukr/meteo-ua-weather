"""Weather platform for Meteo UA."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_NAME, CONF_CITY_SLUG
from .coordinator import MeteoUaCoordinator

_LOGGER = logging.getLogger(__name__)

ADDON_API_BASE = "http://localhost:5581"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MeteoUaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoUaWeather(coordinator, entry)])


class MeteoUaWeather(CoordinatorEntity[MeteoUaCoordinator], WeatherEntity):
    """Current weather entity from meteo.gov.ua."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.MMHG
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator: MeteoUaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._city_id = entry.data[CONF_CITY_ID]
        self._city_slug = entry.data[CONF_CITY_SLUG]
        self._attr_unique_id = f"meteo_ua_weather_{self._city_slug}"
        self._attr_name = f"Meteo UA {entry.data[CONF_CITY_NAME]}"
        self._attr_attribution = "meteo.gov.ua / meteo.ua"

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
    def extra_state_attributes(self) -> dict:
        cur = self.coordinator.data.get("current", {})
        return {
            "condition_text": cur.get("condition_text", ""),
            "wind_direction": cur.get("wind_direction", ""),
        }

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return daily forecast — prefer addon API (has templow), fallback to coordinator."""
        session = async_get_clientsession(self.hass)
        url = f"{ADDON_API_BASE}/api/daily/{self._city_id}/{self._city_slug}"

        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        forecasts: list[Forecast] = []
                        for item in data:
                            fc = Forecast(
                                datetime=item.get("datetime"),
                                condition=item.get("condition"),
                                native_temperature=item.get("temperature"),
                                native_wind_speed=item.get("wind_speed"),
                            )
                            if item.get("templow") is not None:
                                fc["templow"] = item["templow"]
                            forecasts.append(fc)
                        return forecasts
        except Exception as exc:
            _LOGGER.debug("Addon daily unavailable, using coordinator: %s", exc)

        # Fallback to coordinator monthly data
        monthly = self.coordinator.data.get("monthly", {})
        raw = monthly.get("forecast", [])
        if not raw:
            return []

        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        forecasts = []
        for i, item in enumerate(raw):
            temp_str = str(item.get("temp", "0"))
            temp_match = re.search(r"[+-]?\d+", temp_str)
            temp = float(temp_match.group()) if temp_match else None

            wind_str = str(item.get("wind", ""))
            wind_match = re.search(r"[\d.]+", wind_str)
            wind_speed = float(wind_match.group()) if wind_match else None

            dt = today + timedelta(days=i)
            forecasts.append(
                Forecast(
                    datetime=dt.isoformat(),
                    condition=item.get("ha_condition"),
                    native_temperature=temp,
                    native_wind_speed=wind_speed,
                )
            )
        return forecasts

    async def async_forecast_hourly(self) -> list[Forecast]:
        """Return hourly forecast from meteo-ua-parser add-on."""
        session = async_get_clientsession(self.hass)
        url = f"{ADDON_API_BASE}/api/hourly/{self._city_id}/{self._city_slug}"

        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Addon API returned %s for hourly", resp.status)
                    return []
                data = await resp.json()
        except Exception as exc:
            _LOGGER.warning("Failed to fetch hourly from addon: %s", exc)
            return []

        forecasts: list[Forecast] = []
        for item in data:
            forecasts.append(
                Forecast(
                    datetime=item.get("datetime"),
                    condition=item.get("condition"),
                    native_temperature=item.get("temperature"),
                    humidity=item.get("humidity"),
                    native_pressure=item.get("pressure"),
                    native_wind_speed=item.get("wind_speed"),
                    wind_bearing=item.get("wind_bearing"),
                )
            )
        return forecasts
