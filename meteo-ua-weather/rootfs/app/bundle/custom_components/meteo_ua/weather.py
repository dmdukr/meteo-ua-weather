"""Weather platform for Meteo UA."""
from __future__ import annotations

from typing import Any

from homeassistant.components.weather import WeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CITY_NAME, CONF_CITY_SLUG
from .coordinator import MeteoUaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MeteoUaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoUaWeather(coordinator, entry)])


class MeteoUaWeather(CoordinatorEntity[MeteoUaCoordinator], WeatherEntity):
    """Current weather + 30-day forecast in attributes."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.MMHG
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

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
