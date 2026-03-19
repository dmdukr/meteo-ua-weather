/**
 * METEO UA WEATHER FORECAST CARD v0.4.4
 * Custom Lovelace card — hourly forecast + 30-day grid
 * Part of meteo-ua-weather integration
 *
 * Hourly: subscribes to weather/subscribe_forecast (HA native)
 * Daily:  reads entity.attributes.forecast (meteo.ua monthly data)
 *
 * Note: This card uses innerHTML for Lovelace rendering. All data comes from
 * trusted Home Assistant entity state — no user-supplied HTML is rendered.
 */

const CARD_VERSION = "0.4.4";
const CARD_TYPE = "meteo-ua-weather-forecast-card";
const EDITOR_TYPE = "meteo-ua-weather-forecast-card-editor";

/* ── Icon & color maps ─────────────────────────────────── */

const CONDITION_ICONS = {
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
  hail: "mdi:weather-hail",
  "clear-night": "mdi:weather-night",
  windy: "mdi:weather-windy",
  "windy-variant": "mdi:weather-windy-variant",
  exceptional: "mdi:alert-circle-outline",
};

const CONDITION_COLORS = {
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
  hail: "#90caf9",
  "clear-night": "#5c6bc0",
  windy: "#4db6ac",
  "windy-variant": "#4db6ac",
  exceptional: "#ef5350",
};

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

/* ── Main card ─────────────────────────────────────────── */

class MeteoUaWeatherForecastCard extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._hourlyData = [];
    this._unsubHourly = null;
    this._connected = false;
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;
    if (oldHass?.states?.[this._config.entity]?.last_updated !==
        hass?.states?.[this._config.entity]?.last_updated) {
      this._subscribeHourly();
    }
    this._render();
  }

  setConfig(config) {
    if (!config.entity) throw new Error("entity is required");
    this._config = {
      entity: config.entity,
      name: config.name,
      show_hourly: config.show_hourly !== false,
      hourly_slots: config.hourly_slots || 24,
      show_daily: config.show_daily !== false,
      daily_columns: config.daily_columns || 6,
      daily_slots: config.daily_slots || 30,
      show_wind: config.show_wind !== false,
      compact: config.compact || false,
      show_current: config.show_current !== false,
      show_attributes: config.show_attributes !== false,
    };
    this._subscribeHourly();
    this._render();
  }

  connectedCallback() {
    this._connected = true;
    this._subscribeHourly();
  }

  disconnectedCallback() {
    this._connected = false;
    this._unsubscribeHourly();
  }

  _unsubscribeHourly() {
    if (this._unsubHourly) {
      this._unsubHourly.then(function(unsub) { if (unsub) unsub(); });
      this._unsubHourly = null;
    }
  }

  _subscribeHourly() {
    this._unsubscribeHourly();
    if (!this._hass || !this._config.entity || !this._config.show_hourly || !this._connected) return;
    try {
      this._unsubHourly = this._hass.connection.subscribeMessage(
        (event) => {
          this._hourlyData = event?.forecast || [];
          this._render();
        },
        {
          type: "weather/subscribe_forecast",
          forecast_type: "hourly",
          entity_id: this._config.entity,
        }
      );
    } catch (e) {
      console.warn("Meteo UA: hourly subscribe failed", e);
    }
  }

  getCardSize() { return 8; }
  static getConfigElement() { return document.createElement(EDITOR_TYPE); }
  static getStubConfig() { return { entity: "", daily_columns: 6, daily_slots: 30, hourly_slots: 24 }; }

  _render() {
    if (!this._hass || !this._config) return;
    const entity = this._hass.states[this._config.entity];
    if (!entity) {
      this.textContent = "";
      const card = document.createElement("ha-card");
      const div = document.createElement("div");
      div.style.cssText = "padding:16px;color:var(--error-color)";
      div.textContent = "Entity " + this._config.entity + " not found";
      card.appendChild(div);
      this.appendChild(card);
      return;
    }

    const c = this._config;
    const lang = this._hass.language || "uk";

    // Build using DOM
    const card = document.createElement("ha-card");

    // ── Current weather ──
    if (c.show_current) {
      card.appendChild(this._buildCurrent(entity, c));
    }

    // ── Hourly forecast ──
    if (c.show_hourly && this._hourlyData.length > 0) {
      const hourlyEl = this._buildHourly(this._hourlyData, c, lang);
      if (hourlyEl) card.appendChild(hourlyEl);
    }

    // ── Daily grid ──
    if (c.show_daily) {
      const forecast = entity.attributes.forecast || [];
      if (forecast.length > 0) {
        card.appendChild(this._buildDailyGrid(forecast, c));
      }
    }

    // Style
    const style = document.createElement("style");
    style.textContent = this._getStyles(c);
    card.appendChild(style);

    this.textContent = "";
    this.appendChild(card);
  }

  _buildCurrent(entity, c) {
    const wrap = document.createElement("div");
    wrap.className = "mu-current";

    const icon = CONDITION_ICONS[entity.state] || "mdi:weather-cloudy";
    const color = CONDITION_COLORS[entity.state] || "#78909c";
    const temp = entity.attributes.temperature != null ? Math.round(entity.attributes.temperature) : "\u2014";
    const name = c.name || entity.attributes.friendly_name || "";
    const condText = entity.attributes.condition_text || entity.state || "";

    const main = document.createElement("div");
    main.className = "mu-current-main";

    const iconEl = document.createElement("ha-icon");
    iconEl.setAttribute("icon", icon);
    iconEl.style.cssText = "color:" + color + ";--mdc-icon-size:48px";
    main.appendChild(iconEl);

    const info = document.createElement("div");
    info.className = "mu-current-info";
    const tempDiv = document.createElement("div");
    tempDiv.className = "mu-current-temp";
    tempDiv.textContent = temp + "\u00b0";
    info.appendChild(tempDiv);
    const condDiv = document.createElement("div");
    condDiv.className = "mu-current-cond";
    condDiv.textContent = condText;
    info.appendChild(condDiv);
    const nameDiv = document.createElement("div");
    nameDiv.className = "mu-current-name";
    nameDiv.textContent = name;
    info.appendChild(nameDiv);
    main.appendChild(info);
    wrap.appendChild(main);

    if (c.show_attributes) {
      const a = entity.attributes;
      const attrsDiv = document.createElement("div");
      attrsDiv.className = "mu-attrs";
      if (a.humidity != null) attrsDiv.appendChild(this._attrEl("mdi:water-percent", a.humidity + "%"));
      if (a.pressure != null) attrsDiv.appendChild(this._attrEl("mdi:gauge", Math.round(a.pressure) + " hPa"));
      if (a.wind_speed != null) attrsDiv.appendChild(this._attrEl("mdi:weather-windy", a.wind_speed + " km/h " + (a.wind_direction || "")));
      if (attrsDiv.children.length) wrap.appendChild(attrsDiv);
    }
    return wrap;
  }

  _attrEl(icon, text) {
    const d = document.createElement("div");
    d.className = "mu-attr";
    const ic = document.createElement("ha-icon");
    ic.setAttribute("icon", icon);
    ic.style.cssText = "--mdc-icon-size:18px";
    d.appendChild(ic);
    const sp = document.createElement("span");
    sp.textContent = " " + text;
    d.appendChild(sp);
    return d;
  }

  _buildHourly(data, c, lang) {
    const now = new Date();
    const startHour = new Date(now.getTime() - 3600000);
    const filtered = data.filter(function(h) { return new Date(h.datetime) >= startHour; }).slice(0, c.hourly_slots);
    if (!filtered.length) return null;

    const wrap = document.createElement("div");
    wrap.className = "mu-hourly-wrap";
    const row = document.createElement("div");
    row.className = "mu-hourly";

    filtered.forEach(function(h) {
      const dt = new Date(h.datetime);
      const isNewDay = dt.getHours() === 0;
      const icon = CONDITION_ICONS[h.condition] || "mdi:weather-cloudy";
      const color = CONDITION_COLORS[h.condition] || "#78909c";

      const item = document.createElement("div");
      item.className = "mu-hour" + (isNewDay ? " mu-hour-newday" : "");

      const timeDiv = document.createElement("div");
      if (isNewDay) {
        timeDiv.className = "mu-hour-day";
        timeDiv.textContent = dt.toLocaleDateString(lang, { weekday: "short" });
      } else {
        timeDiv.className = "mu-hour-time";
        timeDiv.textContent = dt.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit", hour12: false });
      }
      item.appendChild(timeDiv);

      const ic = document.createElement("ha-icon");
      ic.setAttribute("icon", icon);
      ic.style.cssText = "color:" + color + ";--mdc-icon-size:22px";
      item.appendChild(ic);

      const tempDiv = document.createElement("div");
      tempDiv.className = "mu-hour-temp";
      tempDiv.textContent = (h.temperature != null ? Math.round(h.temperature) : "\u2014") + "\u00b0";
      item.appendChild(tempDiv);

      if (h.wind_speed != null) {
        const windDiv = document.createElement("div");
        windDiv.className = "mu-hour-wind";
        windDiv.textContent = Math.round(h.wind_speed);
        item.appendChild(windDiv);
      }

      row.appendChild(item);
    });

    wrap.appendChild(row);
    return wrap;
  }

  _buildDailyGrid(forecast, c) {
    const section = document.createElement("div");
    section.className = "mu-daily-section";
    const grid = document.createElement("div");
    grid.className = "mu-daily-grid";
    grid.style.gridTemplateColumns = "repeat(" + c.daily_columns + ",1fr)";

    forecast.slice(0, c.daily_slots).forEach(function(d, i) {
      const icon = CONDITION_ICONS[d.ha_condition] || "mdi:weather-cloudy";
      const color = CONDITION_COLORS[d.ha_condition] || "#78909c";

      const day = document.createElement("div");
      day.className = i === 0 ? "mu-day mu-today" : "mu-day";

      const dateDiv = document.createElement("div");
      dateDiv.className = "mu-day-date";
      dateDiv.textContent = d.date || String(d.day);
      day.appendChild(dateDiv);

      const ic = document.createElement("ha-icon");
      ic.setAttribute("icon", icon);
      ic.style.cssText = "color:" + color + ";--mdc-icon-size:" + (c.compact ? 20 : 26) + "px";
      day.appendChild(ic);

      const tempDiv = document.createElement("div");
      tempDiv.className = "mu-day-temp";
      tempDiv.textContent = (d.temp || "\u2014") + "\u00b0";
      day.appendChild(tempDiv);

      if (c.show_wind && d.wind) {
        const windDiv = document.createElement("div");
        windDiv.className = "mu-day-wind";
        windDiv.textContent = d.wind;
        day.appendChild(windDiv);
      }

      grid.appendChild(day);
    });

    section.appendChild(grid);
    return section;
  }

  _getStyles(c) {
    return [
      "ha-card{overflow:hidden}",
      ".mu-current{padding:16px}",
      ".mu-current-main{display:flex;align-items:center;gap:12px}",
      ".mu-current-info{flex:1}",
      ".mu-current-temp{font-size:2.2em;font-weight:600;line-height:1}",
      ".mu-current-cond{font-size:.95em;color:var(--secondary-text-color);margin-top:2px}",
      ".mu-current-name{font-size:.8em;color:var(--secondary-text-color);opacity:.7}",
      ".mu-attrs{display:flex;gap:16px;margin-top:8px;flex-wrap:wrap}",
      ".mu-attr{display:flex;align-items:center;gap:4px;font-size:.85em;color:var(--secondary-text-color)}",
      ".mu-hourly-wrap{padding:0 12px 8px;overflow-x:auto;scrollbar-width:thin}",
      ".mu-hourly{display:flex;gap:2px;min-width:max-content}",
      ".mu-hour{display:flex;flex-direction:column;align-items:center;min-width:52px;padding:6px 4px;border-radius:8px}",
      ".mu-hour:hover{background:var(--secondary-background-color,rgba(0,0,0,.04))}",
      ".mu-hour-newday{background:var(--primary-color,#03a9f4)!important;color:var(--text-primary-color,#fff);border-radius:8px}",
      ".mu-hour-newday .mu-hour-day,.mu-hour-newday .mu-hour-temp,.mu-hour-newday .mu-hour-wind{color:inherit}",
      ".mu-hour-time{font-size:.75em;color:var(--secondary-text-color);margin-bottom:2px}",
      ".mu-hour-day{font-size:.75em;font-weight:600;margin-bottom:2px}",
      ".mu-hour-temp{font-size:.9em;font-weight:500;margin-top:2px}",
      ".mu-hour-wind{font-size:.65em;color:var(--secondary-text-color);margin-top:1px}",
      ".mu-daily-section{padding:4px 12px 12px}",
      ".mu-daily-grid{display:grid;gap:" + (c.compact ? 4 : 6) + "px}",
      ".mu-day{display:flex;flex-direction:column;align-items:center;padding:" + (c.compact ? "4px 2px" : "8px 4px") + ";border-radius:8px;background:var(--secondary-background-color,rgba(0,0,0,.04));transition:background .2s}",
      ".mu-day:hover{background:var(--divider-color,rgba(0,0,0,.08))}",
      ".mu-today{background:var(--primary-color,#03a9f4)!important;color:var(--text-primary-color,#fff)}",
      ".mu-today .mu-day-date,.mu-today .mu-day-temp,.mu-today .mu-day-wind{color:inherit}",
      ".mu-day-date{font-size:" + (c.compact ? .65 : .75) + "em;color:var(--secondary-text-color);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;text-align:center}",
      ".mu-day-temp{font-size:" + (c.compact ? .9 : 1.1) + "em;font-weight:600;color:var(--primary-text-color);margin:2px 0}",
      ".mu-day-wind{font-size:.6em;color:var(--secondary-text-color)}",
    ].join("\n");
  }
}

/* ── Editor ────────────────────────────────────────────── */

class MeteoUaWeatherForecastCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
  }

  set hass(hass) { this._hass = hass; this._render(); }

  setConfig(config) {
    this._config = Object.assign({}, config);
    this._render();
  }

  _render() {
    if (!this._hass) return;
    const c = this._config;
    const uk = this._hass.language === "uk";
    const t = function(ukT, enT) { return uk ? ukT : enT; };

    // Clear and rebuild with DOM
    while (this.firstChild) this.removeChild(this.firstChild);

    const root = document.createElement("div");
    root.className = "mu-editor";

    // Entity selector
    root.appendChild(this._fieldSelect(t("Сутність", "Entity") + " *", "entity", c.entity,
      Object.keys(this._hass.states).filter(function(e) { return e.startsWith("weather."); }).map(function(e) {
        return { value: e, label: this._hass.states[e].attributes.friendly_name || e };
      }.bind(this))
    ));

    // Name
    root.appendChild(this._fieldText(t("Назва", "Name"), "name", c.name || "", t("Автоматично", "Auto")));

    // Hourly group
    root.appendChild(this._group(t("Погодинний прогноз", "Hourly forecast"), [
      this._fieldToggle(t("Показувати погодинний прогноз", "Show hourly forecast"), "show_hourly", c.show_hourly !== false),
      this._fieldNumber(t("Кількість годин", "Hourly slots"), "hourly_slots", c.hourly_slots || 24, 1, 48),
    ]));

    // Daily group
    root.appendChild(this._group(t("Поденний прогноз", "Daily forecast"), [
      this._fieldToggle(t("Показувати поденний прогноз", "Show daily forecast"), "show_daily", c.show_daily !== false),
      this._fieldNumber(t("Кількість днів", "Daily slots"), "daily_slots", c.daily_slots || 30, 1, 30),
      this._fieldRange(t("Днів у рядку", "Days per row"), "daily_columns", c.daily_columns || 6, 3, 10),
      this._fieldToggle(t("Показувати вітер", "Show wind"), "show_wind", c.show_wind !== false),
      this._fieldToggle(t("Компактний режим", "Compact mode"), "compact", c.compact === true),
    ]));

    // Current weather group
    root.appendChild(this._group(t("Поточна погода", "Current weather"), [
      this._fieldToggle(t("Показувати поточну погоду", "Show current weather"), "show_current", c.show_current !== false),
      this._fieldToggle(t("Показувати атрибути", "Show attributes"), "show_attributes", c.show_attributes !== false),
    ]));

    // Styles
    const style = document.createElement("style");
    style.textContent = [
      ".mu-editor{padding:8px 0}",
      ".mu-field{margin:8px 0}",
      ".mu-field label{display:block;font-size:.85em;color:var(--secondary-text-color);margin-bottom:4px}",
      ".mu-field select,.mu-field input[type=text],.mu-field input[type=number]{width:100%;padding:8px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font-size:1em;box-sizing:border-box}",
      ".mu-field input[type=range]{width:calc(100% - 40px);vertical-align:middle}",
      ".mu-range-val{display:inline-block;width:30px;text-align:center;font-weight:600}",
      ".mu-group{margin:8px 0;border:1px solid var(--divider-color);border-radius:8px;overflow:hidden}",
      ".mu-group summary{padding:12px 16px;cursor:pointer;font-weight:500;background:var(--secondary-background-color)}",
      ".mu-group-body{padding:8px 16px 12px}",
      ".mu-toggle{display:flex;align-items:center;gap:8px;padding:6px 0;cursor:pointer}",
      ".mu-toggle input{width:18px;height:18px}",
    ].join("\n");
    root.appendChild(style);

    this.appendChild(root);
  }

  _fireChanged() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: Object.assign({}, this._config) } }));
  }

  _fieldSelect(label, key, value, options) {
    const d = document.createElement("div");
    d.className = "mu-field";
    const l = document.createElement("label");
    l.textContent = label;
    d.appendChild(l);
    const sel = document.createElement("select");
    options.forEach(function(opt) {
      const o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.label;
      if (opt.value === value) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener("change", function() {
      this._config = Object.assign({}, this._config);
      this._config[key] = sel.value;
      this._fireChanged();
    }.bind(this));
    d.appendChild(sel);
    return d;
  }

  _fieldText(label, key, value, placeholder) {
    const d = document.createElement("div");
    d.className = "mu-field";
    const l = document.createElement("label");
    l.textContent = label;
    d.appendChild(l);
    const inp = document.createElement("input");
    inp.type = "text";
    inp.value = value;
    inp.placeholder = placeholder || "";
    inp.addEventListener("change", function() {
      this._config = Object.assign({}, this._config);
      this._config[key] = inp.value;
      this._fireChanged();
    }.bind(this));
    d.appendChild(inp);
    return d;
  }

  _fieldNumber(label, key, value, min, max) {
    const d = document.createElement("div");
    d.className = "mu-field";
    const l = document.createElement("label");
    l.textContent = label;
    d.appendChild(l);
    const inp = document.createElement("input");
    inp.type = "number";
    inp.value = value;
    inp.min = min;
    inp.max = max;
    inp.addEventListener("change", function() {
      this._config = Object.assign({}, this._config);
      this._config[key] = parseInt(inp.value, 10);
      this._fireChanged();
    }.bind(this));
    d.appendChild(inp);
    return d;
  }

  _fieldRange(label, key, value, min, max) {
    const d = document.createElement("div");
    d.className = "mu-field";
    const l = document.createElement("label");
    l.textContent = label;
    d.appendChild(l);
    const inp = document.createElement("input");
    inp.type = "range";
    inp.value = value;
    inp.min = min;
    inp.max = max;
    inp.step = "1";
    const span = document.createElement("span");
    span.className = "mu-range-val";
    span.textContent = value;
    inp.addEventListener("input", function() {
      span.textContent = inp.value;
      this._config = Object.assign({}, this._config);
      this._config[key] = parseInt(inp.value, 10);
      this._fireChanged();
    }.bind(this));
    d.appendChild(inp);
    d.appendChild(span);
    return d;
  }

  _fieldToggle(label, key, checked) {
    const l = document.createElement("label");
    l.className = "mu-toggle";
    const inp = document.createElement("input");
    inp.type = "checkbox";
    inp.checked = checked;
    inp.addEventListener("change", function() {
      this._config = Object.assign({}, this._config);
      this._config[key] = inp.checked;
      this._fireChanged();
    }.bind(this));
    l.appendChild(inp);
    const sp = document.createElement("span");
    sp.textContent = label;
    l.appendChild(sp);
    return l;
  }

  _group(title, children) {
    const det = document.createElement("details");
    det.className = "mu-group";
    const sum = document.createElement("summary");
    sum.textContent = title;
    det.appendChild(sum);
    const body = document.createElement("div");
    body.className = "mu-group-body";
    children.forEach(function(ch) { body.appendChild(ch); });
    det.appendChild(body);
    return det;
  }
}

/* ── Register ──────────────────────────────────────────── */

customElements.define(CARD_TYPE, MeteoUaWeatherForecastCard);
customElements.define(EDITOR_TYPE, MeteoUaWeatherForecastCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: CARD_TYPE,
  name: "Meteo UA Weather Forecast",
  description: "Hourly + 30-day weather forecast (meteo.ua)",
  preview: true,
});

console.info(
  "%c METEO UA WEATHER FORECAST %c v" + CARD_VERSION + " ",
  "color:#fff;background:#1565c0;padding:4px 8px;border-radius:4px 0 0 4px;font-weight:700",
  "color:#1565c0;background:#e3f2fd;padding:4px 8px;border-radius:0 4px 4px 0"
);
