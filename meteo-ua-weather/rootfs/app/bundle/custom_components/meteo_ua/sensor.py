"""Sensor platform for Meteo UA — 30-day forecast."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CITY_NAME, CONF_CITY_SLUG
from .coordinator import MeteoUaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MeteoUaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoUaForecastSensor(coordinator, entry)])


class MeteoUaForecastSensor(CoordinatorEntity[MeteoUaCoordinator], SensorEntity):
    """Sensor with 30-day forecast in attributes."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-month"

    def __init__(self, coordinator: MeteoUaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"meteo_ua_monthly_{entry.data[CONF_CITY_SLUG]}"
        self._attr_name = f"Meteo UA {entry.data[CONF_CITY_NAME]} прогноз на місяць"

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("monthly", {}).get("days", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        m = self.coordinator.data.get("monthly", {})
        return {"forecast": m.get("forecast", []), "city": m.get("city", "")}
