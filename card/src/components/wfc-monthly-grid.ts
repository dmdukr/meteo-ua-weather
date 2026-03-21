import { html, LitElement, nothing, svg, TemplateResult, SVGTemplateResult, css } from "lit";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { customElement, property } from "lit/decorators.js";
import {
  ExtendedHomeAssistant,
  WeatherForecastCardConfig,
  WeatherForecastCardMonthlyGridConfig,
} from "../types";
import { ForecastAttribute } from "../data/weather";

import "./wfc-wind-indicator";
import { getAnimatedWeatherIcon } from "./weather-animated-icons";

// --- Temperature color thresholds ---
interface TempColorStop {
  max: number;
  color: string;
}

const TEMP_COLORS: TempColorStop[] = [
  { max: -10, color: "#50a7e7" },
  { max: 0, color: "#78c2f7" },
  { max: 8, color: "#f5e764" },
  { max: 18, color: "#6dbb6d" },
  { max: 26, color: "#f8a430" },
  { max: Infinity, color: "#ea5a53" },
];

const tempToColor = (temp: number): string => {
  for (const stop of TEMP_COLORS) {
    if (temp <= stop.max) return stop.color;
  }
  return TEMP_COLORS[TEMP_COLORS.length - 1]!.color;
};

// Ukrainian short day/month names
const UK_DAYS_SHORT = ["Нд", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];
const UK_MONTHS_SHORT = [
  "січ", "лют", "бер", "кві", "тра", "чер",
  "лип", "сер", "вер", "жов", "лис", "гру",
];

const isToday = (dt: Date): boolean => {
  const now = new Date();
  return (
    dt.getFullYear() === now.getFullYear() &&
    dt.getMonth() === now.getMonth() &&
    dt.getDate() === now.getDate()
  );
};

// Catmull-Rom to cubic Bezier conversion for smooth curves
const catmullRomToBezier = (
  points: [number, number][]
): string => {
  if (points.length < 2) return "";
  if (points.length === 2) {
    return `M${points[0]![0]},${points[0]![1]} L${points[1]![0]},${points[1]![1]}`;
  }

  let d = `M${points[0]![0]},${points[0]![1]}`;

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)]!;
    const p1 = points[i]!;
    const p2 = points[Math.min(points.length - 1, i + 1)]!;
    const p3 = points[Math.min(points.length - 1, i + 2)]!;

    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;

    d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`;
  }

  return d;
};

@customElement("wfc-monthly-grid")
export class WfcMonthlyGrid extends LitElement {
  @property({ attribute: false }) hass!: ExtendedHomeAssistant;
  @property({ attribute: false }) config!: WeatherForecastCardConfig;
  @property({ attribute: false }) dailyForecast: ForecastAttribute[] = [];
  @property({ attribute: false }) hourlyForecast: ForecastAttribute[] = [];
  @property({ attribute: false }) selectedDate?: string;

  static styles = css`
    .day-cell.selected {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        box-shadow: inset 0 0 0 2px var(--primary-color, #03a9f4);
      }
      
      :host {
      display: block;
      width: 100%;
    }

        .sun {
      fill: var(--weather-icon-sun-color, #fdd93c);
    }
    .moon {
      fill: var(--weather-icon-moon-color, #fcf497);
    }
    .cloud-back {
      fill: var(--weather-icon-cloud-back-color, #d4d4d4);
    }
    .cloud-front {
      fill: var(--weather-icon-cloud-front-color, #f9f9f9);
    }
    .snow {
      fill: var(--weather-icon-snow-color, #f9f9f9);
      stroke: var(--weather-icon-snow-stroke-color, #d4d4d4);
      stroke-width: 1;
      paint-order: stroke;
    }
    .rain {
      fill: var(--weather-icon-rain-color, #30b3f6);
    }



    .mg-container {
      display: flex;
      flex-direction: column;
      gap: 2px;
      width: 100%;
    }

    .mg-row {
      position: relative;
      display: grid;
      gap: 2px;
      width: 100%;
      border-radius: 12px;
      overflow: hidden;
    }

    .mg-row-svg-bg {
      position: absolute;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      border-radius: 12px;
      overflow: hidden;
    }

    .mg-row-svg-bg svg {
      display: block;
      width: 100%;
      height: 100%;
    }

    .mg-cell {
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 6px 2px;
      cursor: pointer;
      transition: background 0.15s ease;
      min-width: 0;
    }

    .mg-cell:hover {
      background: rgba(255, 255, 255, 0.15);
    }

    .mg-cell.is-today {
      background: rgba(255, 255, 255, 0.22);
      box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.5);
      border-radius: 8px;
    }

    .mg-date {
      font-size: 11px;
      font-weight: 600;
      line-height: 1.2;
      color: var(--primary-text-color, #212121);
      text-align: center;
      white-space: nowrap;
      opacity: 0.9;
    }

    .mg-date-day {
      font-size: 10px;
      font-weight: 400;
      opacity: 0.7;
    }

    .mg-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      pointer-events: none;
      margin: 0;
      overflow: visible;
    }

    .mg-icon svg {
      width: 100%;
      height: 100%;
    }

    .mg-icon.compact {
      width: 26px;
      height: 26px;
    }

    .mg-icon svg {
      display: block;
    }

    .mg-temp {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.2;
      color: var(--primary-text-color, #212121);
      white-space: nowrap;
    }

    .mg-temp-low {
      font-size: var(--ha-font-size-s, 11px);
      font-weight: 400;
      color: #ffffff;
    }

    .mg-wind {
      margin-top: 2px;
    }

    .mg-wind.compact {
      transform: scale(0.8);
      margin-top: 0;
    }

    /* compact mode */
    .mg-cell.compact {
      padding: 4px 1px;
    }

    .mg-cell.compact .mg-date {
      font-size: 10px;
    }

    .mg-cell.compact .mg-temp {
      font-size: 11px;
    }

    /* Clickable day indicator — gold border + tap icon */
    .mg-cell.has-hourly {
      box-shadow: inset 0 0 0 1.5px rgba(255, 193, 7, 0.6);
      border-radius: 8px;
    }

    .mg-cell.has-hourly:hover {
      box-shadow: inset 0 0 0 2px rgba(255, 193, 7, 0.85);
    }

    .mg-tap-icon {
      position: absolute;
      top: 2px;
      right: 3px;
      width: 12px;
      height: 12px;
      opacity: 0.5;
      pointer-events: none;
    }
  `;

  private get gridConfig(): Required<WeatherForecastCardMonthlyGridConfig> {
    const cfg = this.config?.monthly_grid;
    return {
      show: cfg?.show !== false,
      columns: cfg?.columns ?? 6,
      show_wind: cfg?.show_wind !== false,
      compact: cfg?.compact ?? false,
      show_chart: cfg?.show_chart !== false,
    };
  }

  protected render(): TemplateResult | typeof nothing {
    const gc = this.gridConfig;
    if (!gc.show) return nothing;

    const forecast = this.dailyForecast;
    if (!forecast || forecast.length === 0) return nothing;

    // Split forecast into rows
    const rows: ForecastAttribute[][] = [];
    for (let i = 0; i < forecast.length; i += gc.columns) {
      rows.push(forecast.slice(i, i + gc.columns));
    }

    return html`
      <div class="mg-container">
        ${rows.map((row) => this.renderRow(row, gc))}
      </div>
    `;
  }

  private renderRow(
    row: ForecastAttribute[],
    gc: Required<WeatherForecastCardMonthlyGridConfig>
  ): TemplateResult {
    const cols = gc.columns;

    return html`
      <div
        class="mg-row"
        style="grid-template-columns: repeat(${cols}, 1fr)"
      >
        ${gc.show_chart ? this.renderWaveSVG(row, cols) : nothing}
        ${row.map((f) => this.renderCell(f, gc))}
      </div>
    `;
  }

  private renderCell(
    forecast: ForecastAttribute,
    gc: Required<WeatherForecastCardMonthlyGridConfig>
  ): TemplateResult {
    const dt = new Date(forecast.datetime);
    const dayName = UK_DAYS_SHORT[dt.getDay()]!;
    const dateStr = `${dt.getDate()} ${UK_MONTHS_SHORT[dt.getMonth()]!}`;
    const today = isToday(dt);
    const compact = gc.compact;

    const tempHigh = Math.round(forecast.temperature);
    const tempLow = forecast.templow != null ? Math.round(forecast.templow) : null;

    const stateObj = this.hass?.states[this.config.entity];
    const dayStr = dt.toDateString();
    const hasHourly = this.hourlyForecast.some(
      (h) => new Date(h.datetime).toDateString() === dayStr
    );
    const isSelected = this.selectedDate && new Date(this.selectedDate).toDateString() === dayStr;

    return html`
      <div
        class="mg-cell ${today ? "is-today" : ""} ${compact ? "compact" : ""} ${isSelected ? "selected" : ""} ${hasHourly ? "has-hourly" : ""}"
        @click=${() => this.onDayClick(forecast)}
      >
        ${hasHourly ? html`<svg class="mg-tap-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path fill="currentColor" d="M10.5 8.5a2 2 0 1 1 4 0v2.25a.75.75 0 0 0 1.5 0V9a1.25 1.25 0 0 1 2.5 0v3.5a5.5 5.5 0 0 1-5.5 5.5H12a5.5 5.5 0 0 1-4.9-3l-1.85-3.7a1.25 1.25 0 0 1 1.82-1.6L9 11.62V8.5a1.25 1.25 0 0 1 1.5-1.23Z"/>
        </svg>` : nothing}
        <div class="mg-date">
          <span class="mg-date-day">${dayName}</span> ${dateStr}
        </div>
        <div class="mg-icon ${compact ? "compact" : ""}">
          ${unsafeHTML(getAnimatedWeatherIcon(forecast.condition || "cloudy", compact ? 22 : 32, true))}
        </div>
        <div class="mg-temp">
          ${tempLow != null
            ? html`<span class="mg-temp-low">${tempLow}°...</span>${tempHigh}°`
            : html`${tempHigh}°`}
        </div>
        ${gc.show_wind && forecast.wind_speed != null && stateObj
          ? html`
              <div class="mg-wind ${compact ? "compact" : ""}">
                <wfc-wind-indicator
                  .hass=${this.hass}
                  .weatherEntity=${stateObj}
                  .forecast=${forecast}
                  .size=${compact ? 26 : 32}
                  .radius=${compact ? 14 : 17}
                  type="bearing"
                ></wfc-wind-indicator>
              </div>
            `
          : nothing}
      </div>
    `;
  }

  // SVG temperature wave background for a row
  private renderWaveSVG(
    row: ForecastAttribute[],
    cols: number
  ): TemplateResult {
    if (row.length === 0) return html``;

    const svgW = 1000;
    const svgH = 120;
    const padY = 10;

    // Collect temperatures
    const temps = row.map((f) => f.temperature);
    const tMin = Math.min(...temps);
    const tMax = Math.max(...temps);
    const tRange = tMax === tMin ? 1 : tMax - tMin;

    // Build points: x centered in each column cell, y mapped from temperature
    const cellW = svgW / cols;
    const points: [number, number][] = temps.map((t, i) => {
      const x = cellW * i + cellW / 2;
      // Invert y so higher temp is higher on SVG (lower y value)
      const y = svgH - padY - ((t - tMin) / tRange) * (svgH - padY * 2);
      return [x, y];
    });

    const curvePath = catmullRomToBezier(points);

    // Build area fill path (curve + close to bottom)
    const areaPath = `${curvePath} L${points[points.length - 1]![0]},${svgH} L${points[0]![0]},${svgH} Z`;

    // Build gradient stops from temperatures
    const gradientStops = this.buildGradientStops(temps);

    return html`
      <div class="mg-row-svg-bg">
        ${svg`
          <svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="mg-grad-${this.uniqueId(row)}" x1="0" x2="1" y1="0" y2="0">
                ${gradientStops}
              </linearGradient>
            </defs>
            <path
              d="${areaPath}"
              fill="url(#mg-grad-${this.uniqueId(row)})"
              opacity="0.35"
            />
            <path
              d="${curvePath}"
              fill="none"
              stroke="url(#mg-grad-${this.uniqueId(row)})"
              stroke-width="3"
              opacity="0.7"
            />
          </svg>
        `}
      </div>
    `;
  }

  private buildGradientStops(
    temps: number[]
  ): SVGTemplateResult[] {
    const stops: SVGTemplateResult[] = [];
    const n = temps.length;
    for (let i = 0; i < n; i++) {
      const offset = n === 1 ? 0.5 : i / (n - 1);
      const color = tempToColor(temps[i]!);
      stops.push(
        svg`<stop offset="${offset}" stop-color="${color}" />`
      );
    }
    return stops;
  }

  private uniqueId(row: ForecastAttribute[]): string {
    if (row.length === 0) return "empty";
    return row[0]!.datetime.replace(/[^a-zA-Z0-9]/g, "");
  }

  private onDayClick(forecast: ForecastAttribute): void {
    const event = new CustomEvent("monthly-day-select", {
      detail: { forecast },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "wfc-monthly-grid": WfcMonthlyGrid;
  }
}
