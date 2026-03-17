"""Constants for Meteo UA integration."""

DOMAIN = "meteo_ua"

CONF_CITY_ID = "city_id"
CONF_CITY_SLUG = "city_slug"
CONF_CITY_NAME = "city_name"
UPDATE_INTERVAL_CURRENT = 1800   # 30 min
UPDATE_INTERVAL_FORECAST = 7200  # 2 hours

MONTHLY_URL = "https://meteo.ua/{city_id}/{city_slug}/month"
AUTOCOMPLETE_URL = "https://meteo.ua/front/forecast/autocomplete?phrase={phrase}"

# meteo.ua icon name -> HA weather condition
ICON_TO_HA_CONDITION = {
    "clear-sky": "sunny",
    "few-clouds-11-25": "partlycloudy",
    "scattered-clouds-25-50": "partlycloudy",
    "broken-clouds-51-84": "cloudy",
    "overcast-clouds-85-100": "cloudy",
    "light-rain": "rainy",
    "moderate-rain": "rainy",
    "heavy-rain": "pouring",
    "thunderstorm": "lightning",
    "thunderstorm-with-rain": "lightning-rainy",
    "thunderstorm-with-heavy-rain": "lightning-rainy",
    "light-snow": "snowy",
    "moderate-snow": "snowy",
    "heavy-snow": "snowy",
    "rain-and-snow": "snowy-rainy",
    "sleet": "snowy-rainy",
    "fog": "fog",
    "mist": "fog",
    "haze": "fog",
}

