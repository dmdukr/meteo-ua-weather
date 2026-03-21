# Meteo UA Weather — Home Assistant Add-on

Weather from [meteo.ua](https://meteo.ua) for Home Assistant. 30-day forecast, hourly forecast, animated weather effects, and monthly calendar grid.

On first start automatically installs the **Meteo UA Weather** integration and forecast card.

> 🤖 This add-on — including the weather card refactoring, all Python parsers, integration code, and this repository — was **created with [Claude](https://claude.ai) (Anthropic)**.

---

*[Українська версія нижче / Ukrainian version below](#meteo-ua-weather--home-assistant-додаток)*

---

## Features

- **30-day daily forecast** with animated weather icons and temperature wave chart
- **Hourly forecast** with temperature/precipitation chart, scrollable
- **15 weather effects**: rain, snow, fog, wind, hail, lightning, clouds — with day/night backgrounds
- **Monthly grid**: color-coded temperature waves, wind indicators, clickable days with golden border
- **Night temperatures** in monthly grid (small white font)
- **19 000+ settlements** search via meteo.ua API, top-50 cities by default
- **Dark / Light theme** support

## Installation

1. In Home Assistant go to **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories**
3. Add: `https://github.com/dmdukr/ha-addon-meteo-ua-weather`
4. Find **Meteo UA Weather** and click **Install**
5. Start the add-on
6. Restart Home Assistant when prompted
7. Go to **Settings → Integrations → Add Integration → Meteo UA Weather**
8. Search for your city or select from the top-50 list

## Uninstallation

1. Remove the integration: **Settings → Integrations → Meteo UA Weather → Delete**
2. Remove the add-on: **Settings → Add-ons → Meteo UA Weather → Uninstall**

The integration automatically cleans up the Lovelace card resource and JS file when the last config entry is removed.

## Card Configuration

Add the card to your dashboard via UI editor or YAML:

```yaml
type: custom:meteo-ua-weather-forecast-card
entity: weather.meteo_ua_kyiv
show_current: true
show_forecast: true
show_condition_effects: true
forecast:
  mode: simple
  show_sun_times: true
  use_color_thresholds: true
monthly_grid:
  show: true
  columns: 6
  show_wind: true
  show_chart: true
```

### Weather Effects

All 15 HA weather conditions are supported with animated backgrounds:

| Condition | Day | Night |
|-----------|-----|-------|
| `sunny` / `clear-night` | Sky + sun + rays | Night sky + moon + stars |
| `partlycloudy` | Sky + sun + blurred clouds | Night sky + moon + clouds |
| `cloudy` | Overcast + drifting clouds | Dark overcast + clouds |
| `rainy` / `pouring` | Overcast + rain particles | Dark overcast + rain |
| `snowy` | Overcast + SVG snowflakes | Dark overcast + snowflakes |
| `snowy-rainy` | Overcast + snow + rain | Dark overcast + snow + rain |
| `fog` | Fog gradient + 135 orbs | Dark fog + orbs |
| `lightning` / `lightning-rainy` | Overcast + flash bursts | Dark overcast + flashes |
| `hail` | Overcast + hail particles | Dark overcast + hail |
| `windy` / `windy-variant` | Sky + leaves + streaks | Night sky + moon + leaves |
| `exceptional` | Pulsing amber overlay | Pulsing amber overlay |

### Debug Weather Effects

To preview a specific condition:

```yaml
debug_condition: snowy-rainy
```

Remove the line to return to real weather.

## Monthly Grid

The monthly grid shows 30 days with:
- Animated weather icons
- Day + night temperatures (`3°...10°`)
- Wind direction indicators
- Color-coded temperature wave background
- **Golden border** on days with hourly forecast data (clickable → switches to hourly view)

## Development

| Component | Repository |
|-----------|-----------|
| Card (TypeScript) | [dmdukr/ha-weather-forecast-card](https://github.com/dmdukr/ha-weather-forecast-card) |
| Add-on + Integration | [dmdukr/ha-addon-meteo-ua-weather](https://github.com/dmdukr/ha-addon-meteo-ua-weather) |

All 3 components (card, integration, add-on) share the same version number.

## Bug reports

Found a bug? Open an issue:

**[github.com/dmdukr/ha-addon-meteo-ua-weather/issues](https://github.com/dmdukr/ha-addon-meteo-ua-weather/issues)**

| Field | Where to find |
|-------|--------------|
| **Add-on version** | Settings → Add-ons → Meteo UA Weather → Info |
| **Home Assistant version** | Settings → System → About |
| **Add-on logs** | Settings → Add-ons → Meteo UA Weather → Log tab |
| **Browser console** | F12 → Console → filter by "METEO" |

---

---

# Meteo UA Weather — Home Assistant Додаток

Погода з [meteo.ua](https://meteo.ua) для Home Assistant. 30-денний прогноз, погодинний прогноз, анімовані погодні ефекти та місячний календар.

При першому запуску автоматично встановлює інтеграцію **Meteo UA Weather** та карточку прогнозу.

> 🤖 Цей додаток — включаючи рефакторинг карточки, Python-парсери, код інтеграції та цей репозиторій — **створено за допомогою [Claude](https://claude.ai) (Anthropic)**.

## Можливості

- **30-денний прогноз** з анімованими іконками та хвилею температур
- **Погодинний прогноз** з графіком температури/опадів
- **15 погодних ефектів**: дощ, сніг, туман, вітер, град, блискавка, хмари — з денними/нічними фонами
- **Місячна сітка**: кольорові хвилі температур, індикатори вітру, клікабельні дні із золотою рамкою
- **Нічна температура** в місячній сітці (дрібний білий шрифт)
- **19 000+ населених пунктів** через API meteo.ua, топ-50 міст за замовчуванням
- Підтримка **темної / світлої теми**

## Встановлення

1. В Home Assistant перейди до **Налаштування → Додатки → Магазин додатків**
2. Натисни **⋮ → Repositories**
3. Додай: `https://github.com/dmdukr/ha-addon-meteo-ua-weather`
4. Знайди **Meteo UA Weather** та натисни **Встановити**
5. Запусти додаток
6. Перезавантаж Home Assistant за запитом
7. Перейди до **Налаштування → Інтеграції → Додати інтеграцію → Meteo UA Weather**
8. Знайди своє місто або обери з топ-50 списку

## Видалення

1. Видали інтеграцію: **Налаштування → Інтеграції → Meteo UA Weather → Видалити**
2. Видали додаток: **Налаштування → Додатки → Meteo UA Weather → Видалити**

Інтеграція автоматично видаляє ресурс карточки Lovelace та JS-файл при видаленні останнього запису.

## Налаштування карточки

Додайте карточку через UI-редактор або YAML:

```yaml
type: custom:meteo-ua-weather-forecast-card
entity: weather.meteo_ua_kyiv
show_current: true
show_forecast: true
show_condition_effects: true
forecast:
  mode: simple
  show_sun_times: true
  use_color_thresholds: true
monthly_grid:
  show: true
  columns: 6
  show_wind: true
  show_chart: true
```

### Погодні ефекти

Підтримуються всі 15 станів погоди HA з анімованими фонами:

| Стан | День | Ніч |
|------|------|-----|
| `sunny` / `clear-night` | Небо + сонце + промені | Нічне небо + місяць + зірки |
| `partlycloudy` | Небо + сонце + розмиті хмари | Нічне небо + місяць + хмари |
| `cloudy` | Хмарне + дрейфуючі хмари | Темне хмарне + хмари |
| `rainy` / `pouring` | Хмарне + краплі дощу | Темне хмарне + дощ |
| `snowy` | Хмарне + SVG сніжинки | Темне хмарне + сніжинки |
| `snowy-rainy` | Хмарне + сніг + дощ | Темне хмарне + сніг + дощ |
| `fog` | Туманний градієнт + 135 орбіт | Темний туман + орбіти |
| `lightning` / `lightning-rainy` | Хмарне + спалахи | Темне хмарне + спалахи |
| `hail` | Хмарне + градини | Темне хмарне + градини |
| `windy` / `windy-variant` | Небо + листя + смуги | Нічне небо + місяць + листя |
| `exceptional` | Пульсуючий бурштиновий оверлей | Пульсуючий бурштиновий оверлей |

### Налагодження ефектів

Для перегляду певного ефекту:

```yaml
debug_condition: snowy-rainy
```

Видаліть рядок для повернення до реальної погоди.

## Місячна сітка

Місячна сітка показує 30 днів:
- Анімовані іконки погоди
- Денна + нічна температура (`3°...10°`)
- Індикатори напрямку вітру
- Кольорова хвиля температур на фоні
- **Золота рамка** на днях з погодинним прогнозом (клік → перемикання на погодинний вигляд)

## Розробка

| Компонент | Репозиторій |
|-----------|-----------|
| Карточка (TypeScript) | [dmdukr/ha-weather-forecast-card](https://github.com/dmdukr/ha-weather-forecast-card) |
| Додаток + Інтеграція | [dmdukr/ha-addon-meteo-ua-weather](https://github.com/dmdukr/ha-addon-meteo-ua-weather) |

Всі 3 компоненти (карточка, інтеграція, додаток) мають однаковий номер версії.

## Повідомлення про помилки

Знайшли баг? Відкрийте issue:

**[github.com/dmdukr/ha-addon-meteo-ua-weather/issues](https://github.com/dmdukr/ha-addon-meteo-ua-weather/issues)**

| Поле | Де знайти |
|------|-----------|
| **Версія додатку** | Налаштування → Додатки → Meteo UA Weather → Info |
| **Версія Home Assistant** | Налаштування → Система → Про систему |
| **Логи додатку** | Налаштування → Додатки → Meteo UA Weather → Log |
| **Консоль браузера** | F12 → Console → фільтр "METEO" |
