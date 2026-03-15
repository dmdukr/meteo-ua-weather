"""Config flow for Meteo UA."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN, CONF_CITY_ID, CONF_CITY_SLUG, CONF_CITY_NAME,
    CONF_STATION_ID, DEFAULT_CITY_NAME, DEFAULT_STATION_ID, CITIES,
)


class MeteoUaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow — select city from list or enter custom."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """City selection step."""
        if user_input is not None:
            city_name = user_input[CONF_CITY_NAME]
            city = next((c for c in CITIES if c["name"] == city_name), None)
            if city:
                await self.async_set_unique_id(f"meteo_ua_{city['id']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Meteo UA — {city['name']}",
                    data={
                        CONF_CITY_ID: city["id"],
                        CONF_CITY_SLUG: city["slug"],
                        CONF_CITY_NAME: city["name"],
                        CONF_STATION_ID: city["station"],
                    },
                )
            return await self.async_step_custom()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CITY_NAME, default=DEFAULT_CITY_NAME): vol.In(
                    [c["name"] for c in CITIES]
                ),
            }),
        )

    async def async_step_custom(self, user_input=None):
        """Custom city input step."""
        if user_input is not None:
            await self.async_set_unique_id(f"meteo_ua_{user_input[CONF_CITY_ID]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Meteo UA — {user_input[CONF_CITY_NAME]}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="custom",
            data_schema=vol.Schema({
                vol.Required(CONF_CITY_ID): str,
                vol.Required(CONF_CITY_SLUG): str,
                vol.Required(CONF_CITY_NAME): str,
                vol.Required(CONF_STATION_ID, default=DEFAULT_STATION_ID): str,
            }),
        )
