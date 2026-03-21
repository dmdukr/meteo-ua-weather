# Meteo UA Weather

Home Assistant addon for weather from [meteo.ua](https://meteo.ua).

Automatically installs the **Meteo UA Weather** integration and forecast card on first start.

## Features

- **30-day daily forecast** with animated weather icons
- **Hourly forecast** with temperature chart and precipitation bars
- **Weather effects**: rain, snow, fog, wind, lightning, clouds with day/night backgrounds
- **Monthly grid**: temperature waves, wind indicators, clickable days with golden border
- **Night temperatures** displayed in monthly grid
- **19 000+ settlements** search via meteo.ua API, top-50 cities available by default
- **Dark/Light theme** support

## Installation

1. Add this repository to Home Assistant Add-on Store:
   ```
   https://github.com/dmdukr/ha-addon-meteo-ua-weather
   ```
2. Install **Meteo UA Weather** addon
3. Start the addon
4. Restart Home Assistant when prompted
5. Go to **Settings → Integrations → Add Integration → Meteo UA Weather**
6. Search for your city or select from the top-50 list

## Uninstallation

1. Remove the integration via **Settings → Integrations → Meteo UA Weather → Delete**
2. Remove the addon via **Settings → Add-ons → Meteo UA Weather → Uninstall**

The integration automatically cleans up the Lovelace card resource and JS file when the last config entry is removed.

## Card Configuration

Add the card to your dashboard:

```yaml
type: custom:meteo-ua-weather-forecast-card
entity: weather.meteo_ua_kyiv
show_current: true
show_forecast: true
show_condition_effects: true
monthly_grid:
  show: true
  columns: 6
  show_wind: true
  show_chart: true
```

### Debug Weather Effects

To preview a specific condition's effects:

```yaml
debug_condition: snowy-rainy
```

Remove the line to return to the real weather state.

## Development

- **Card source**: [dmdukr/ha-weather-forecast-card](https://github.com/dmdukr/ha-weather-forecast-card)
- **Addon + Integration**: this repo

All 3 components (card, integration, addon) share the same version number.
