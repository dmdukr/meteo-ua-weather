/**
 * METEO UA WEATHER FORECAST v0.2.1
 * Custom Lovelace card — 30-day weather forecast grid
 * Part of meteo-ua-weather integration
 * Data: sensor with json attr "forecast"
 */

const METEO_ICONS = {
  sunny: "mdi:weather-sunny",
  partlycloudy: "mdi:weather-partly-cloudy",
  cloudy: "mdi:weather-cloudy",
  rainy: "mdi:weather-rainy",
  pouring: "mdi:weather-pouring",
  "lightning-rainy": "mdi:weather-lightning-rainy",
  lightning: "mdi:weather-lightning",
  snowy: "mdi:weather-snowy",
  "snowy-rainy": "mdi:weather-snowy-rainy",
  fog: "mdi:weather-fog",
  "clear-night": "mdi:weather-night",
};

const METEO_COLORS = {
  sunny: "#f9a825",
  partlycloudy: "#90a4ae",
  cloudy: "#78909c",
  rainy: "#42a5f5",
  pouring: "#1565c0",
  "lightning-rainy": "#7e57c2",
  lightning: "#9c27b0",
  snowy: "#b0bec5",
  "snowy-rainy": "#80cbc4",
  fog: "#b0bec5",
  "clear-night": "#5c6bc0",
};

class MeteoUaWeatherForecastCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) throw new Error("entity is required");
    this._config = {
      entity: config.entity,
      columns: config.columns || 6,
      title: config.title !== undefined ? config.title : "Прогноз на місяць",
      show_wind: config.show_wind !== false,
      show_condition: config.show_condition !== false,
      compact: config.compact || false,
    };
  }

  getCardSize() { return 6; }

  static getStubConfig() { return { entity: "", columns: 6 }; }

  _render() {
    if (!this._hass || !this._config) return;

    const entity = this._hass.states[this._config.entity];
    if (!entity) {
      this.innerHTML = `<ha-card><div style="padding:16px;color:var(--error-color)">Entity ${this._config.entity} not found</div></ha-card>`;
      return;
    }

    const forecast = entity.attributes.forecast || [];
    if (!forecast.length) {
      this.innerHTML = `<ha-card><div style="padding:16px">No forecast data</div></ha-card>`;
      return;
    }

    const c = this._config;
    const days = forecast.map((d, i) => {
      const icon = METEO_ICONS[d.ha_condition] || "mdi:weather-cloudy";
      const color = METEO_COLORS[d.ha_condition] || "#78909c";
      const cls = i === 0 ? "mc-day mc-today" : "mc-day";
      let h = `<div class="${cls}">`;
      h += `<div class="mc-date">${d.date || d.day}</div>`;
      h += `<ha-icon icon="${icon}" style="color:${color};--mdc-icon-size:${c.compact ? 20 : 28}px"></ha-icon>`;
      h += `<div class="mc-temp">${d.temp || "—"}°</div>`;
      if (c.show_wind && d.wind) h += `<div class="mc-wind">${d.wind}</div>`;
      if (c.show_condition && !c.compact && d.condition) h += `<div class="mc-cond">${d.condition}</div>`;
      h += "</div>";
      return h;
    }).join("");

    const title = c.title ? `<div class="card-header">${c.title}</div>` : "";
    const gap = c.compact ? 4 : 6;
    const pad = c.compact ? "4px 2px" : "8px 4px";
    const dateSz = c.compact ? 0.65 : 0.75;
    const tempSz = c.compact ? 0.9 : 1.1;

    this.innerHTML = `
      <ha-card>
        ${title}
        <div style="padding:8px 12px 12px">
          <div class="mc-grid" style="grid-template-columns:repeat(${c.columns},1fr)">${days}</div>
        </div>
      </ha-card>
      <style>
        ha-card{overflow:hidden}
        .card-header{padding:12px 16px 0;font-size:1.1em;font-weight:500}
        .mc-grid{display:grid;gap:${gap}px}
        .mc-day{display:flex;flex-direction:column;align-items:center;padding:${pad};border-radius:8px;background:var(--secondary-background-color,rgba(0,0,0,.04));transition:background .2s}
        .mc-day:hover{background:var(--divider-color,rgba(0,0,0,.08))}
        .mc-today{background:var(--primary-color,#03a9f4)!important;color:var(--text-primary-color,#fff)}
        .mc-today .mc-date,.mc-today .mc-temp,.mc-today .mc-wind,.mc-today .mc-cond{color:inherit}
        .mc-date{font-size:${dateSz}em;color:var(--secondary-text-color);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;text-align:center}
        .mc-temp{font-size:${tempSz}em;font-weight:600;color:var(--primary-text-color);margin:2px 0}
        .mc-wind{font-size:.6em;color:var(--secondary-text-color)}
        .mc-cond{font-size:.55em;color:var(--secondary-text-color);text-align:center;line-height:1.2;max-height:2.4em;overflow:hidden}
      </style>`;
  }
}

customElements.define("meteo-ua-weather-forecast-card", MeteoUaWeatherForecastCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "meteo-ua-weather-forecast-card",
  name: "Meteo UA Weather Forecast",
  description: "30-day weather forecast grid (meteo.ua)",
  preview: true,
});

console.info(
  "%c METEO UA WEATHER FORECAST %c v0.2.1 ",
  "color:#fff;background:#1565c0;padding:4px 8px;border-radius:4px 0 0 4px;font-weight:700",
  "color:#1565c0;background:#e3f2fd;padding:4px 8px;border-radius:0 4px 4px 0"
);
