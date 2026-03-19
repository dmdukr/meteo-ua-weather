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
