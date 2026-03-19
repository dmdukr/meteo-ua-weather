## 0.4.5
## 0.4.7

- Fix: all editor helper texts translated to Ukrainian
- No untranslated English strings remaining in editor

## 0.4.6

- Card rebuilt from TypeScript source (troinine/ha-weather-forecast-card)
- Monthly forecast grid: 30-day icons, temperature wave, color-coded
- Editor: Monthly forecast settings (columns, wind, chart, compact)
- Editor: Hourly/Daily expandable groups with UK localization
- All editor labels and helpers translated to Ukrainian


- Restored full card with monthly grid, SVG temperature waves, dynamic icons
- Hourly chart + daily 30-day grid shown simultaneously
- wfc-monthly-grid component with color gradient temperature curves

## 0.4.4

- Rebuilt card from custom base — hourly + daily grid shown simultaneously
- Hourly: scrollable strip with icons, temp, wind
- Daily: 30-day grid with colored icons (6 per row default)
- Editor with collapsible groups and UK localization
- DOM-based rendering (no innerHTML)

## 0.4.3

- Fixed empty expandable group labels (Погодинний/Поденний прогноз)
- Fixed daily_columns slider position (default 6)

## 0.4.2

- Fixed encoding — Ukrainian text now displays correctly
- Rebuilt card from clean source with proper UTF-8

## 0.4.0

- Removed "Weather to show" selector — current weather always shown
- Added "Show hourly forecast" toggle in Hourly group
- Added "Show daily forecast" toggle in Daily group
- Moved forecast display mode (Simple/Chart) to Hourly group
- Added "Days per row" slider (default 6) to Daily group
- Full Ukrainian localization of all labels and helpers

## 0.4.0

- Card: forecast.mode (Простий/Графік) moved to hourly forecast group
- Card: daily_columns — days per row with CSS grid auto-resize
- Card: "Simple"/"Chart" translated to Ukrainian

## 0.3.9

- Card editor: reorganized — General → Поточна погода → Погодинний прогноз → Поденний прогноз
- All helper texts translated to Ukrainian
- Fixed "Extra прогноз атрибут" label

## 0.3.8

- Hourly forecast starts from current_hour - 1

## 0.3.7

- Card editor: Ukrainian localization for all labels
- Card editor: forecast interactions moved into hourly forecast group as "Взаємодія іконок"
- Card editor: clearer group labels

## 0.3.6

- Card editor: hourly forecast settings in collapsible group
- Card editor: daily forecast settings in collapsible group
- Card rebuilt from TypeScript source with renamed custom element

# Changelog

## 0.3.5

- Rebuilt card from TypeScript source (v1.30.0)
- Grouped editor sections: hourly forecast, daily forecast settings
- Hourly + Daily forecast via HA standard weather API
- Parser returns full hourly data from weatherDetailSlider

## 0.3.0

- Full forecast card with dynamic icons and temperature waves
- Single weather entity, single-step config flow

## 0.1.0

- Initial release
