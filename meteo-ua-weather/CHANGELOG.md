# Changelog

## 1.0.0

### Integration
- Two-step config flow: filter → select with top-50 Ukrainian cities
- "Новий пошук" option in dropdown to return to search
- Night temperature parsing (temp_day / temp_night) from meteo.ua
- native_templow in daily forecast
- async_remove_entry: clean Lovelace resource + JS on uninstall
- Cache clear notification on addon update

### Weather Forecast Card
- Deep refactoring: -53% animation provider, -27% chart component
- Removed lodash-es, consola dependencies (native helpers)
- Night backgrounds for all 15 weather conditions
- Blurred edges on partlycloudy clouds
- Monthly grid: golden border + tap icon for clickable days
- Monthly grid: uniform 36x36 icon box, clipTall for tall conditions
- Monthly grid: night temperature in small white font
- Monthly grid: day temperature 15px bold
- 305/305 tests, ESLint 0 errors, 0 vulnerabilities
- Bundle: 384 KB

## 0.5.1

- Fix: ha_condition field for daily forecast icons
- Fix: remove all test modes from weather entity

## 0.5.0

- Removed forecast type selector (hourly/daily) from editor

## 0.4.9

- Attribute entities moved to Current Weather section
- Current temperature precision moved to Current Weather
- Forecast temperature precision moved to Hourly Forecast

## 0.4.8

- Weather effects: rain, snow, clouds, fog, wind, lightning
- Effects translated to Ukrainian

## 0.4.7

- Fix: all editor helper texts translated to Ukrainian

## 0.4.6

- Card rebuilt from TypeScript source
- Monthly forecast grid: 30-day icons, temperature wave, color-coded
- Editor: Monthly forecast settings (columns, wind, chart, compact)
- All editor labels and helpers translated to Ukrainian

## 0.4.4

- Hourly + daily grid shown simultaneously
- Editor with collapsible groups and Ukrainian localization

## 0.3.0

- Full forecast card with dynamic icons and temperature waves
- Single weather entity, single-step config flow

## 0.1.0

- Initial release
