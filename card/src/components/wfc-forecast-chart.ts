import { html, LitElement, nothing, PropertyValues, TemplateResult } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { DragScrollController } from "../controllers/drag-scroll-controller";
import { formatDay } from "../helpers";
import { styleMap } from "lit/directives/style-map.js";
import { classMap } from "lit/directives/class-map.js";
import ChartDataLabels from "chartjs-plugin-datalabels";
import { getRelativePosition } from "chart.js/helpers";
import { actionHandler } from "../hass";
import { logger } from "../logger";
import { ActionHandlerEvent, fireEvent } from "custom-card-helpers";
import {
  CHART_ATTRIBUTES,
  ChartAttributes,
  CurrentWeatherAttributes,
  DEFAULT_CHART_ATTRIBUTE,
  ExtendedHomeAssistant,
  ForecastActionDetails,
  WeatherForecastCardConfig,
} from "../types";
import {
  ForecastAttribute,
  ForecastType,
  WEATHER_ATTRIBUTE_ICON_MAP,
  WeatherEntity,
} from "../data/weather";
import {
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Chart,
  BarController,
  BarElement,
  ChartConfiguration,
} from "chart.js";

import "./wfc-forecast-header-items";
import "./dropdown/wfc-chart-attribute-selector";
import { buildChartConfig, DEFAULT_CHART_FONT_SIZE, ChartBuildContext } from "./chart-config-builder";

Chart.register(
  BarController, BarElement, LineController, LineElement,
  PointElement, LinearScale, CategoryScale, ChartDataLabels
);

const MAX_CANVAS_WIDTH = 16384;
const DEFAULT_CHART_HEIGHT = 130;

@customElement("wfc-forecast-chart")
export class WfcForecastChart extends LitElement {
  @property({ attribute: false }) hass!: ExtendedHomeAssistant;
  @property({ attribute: false }) weatherEntity!: WeatherEntity;
  @property({ attribute: false }) forecast: ForecastAttribute[] = [];
  @property({ attribute: false }) config!: WeatherForecastCardConfig;
  @property({ attribute: false }) forecastType!: ForecastType;
  @property({ attribute: false }) isTwiceDailyEntity = false;
  @property({ attribute: false }) itemWidth: number = 0;
  @property({ attribute: false }) isScrollable = false;
  @query("canvas") private _canvas?: HTMLCanvasElement;

  @state() private _settingsOpen = false;
  @state() private _selectedAttribute: ChartAttributes = DEFAULT_CHART_ATTRIBUTE;

  private _lastChartEvent: PointerEvent | null = null;
  private _chart: Chart | null = null;
  private _temperatureColors: Record<string, string> | null = null;
  private _scrollController = new DragScrollController(this, {
    selector: ".wfc-scroll-container",
    childSelector: ".wfc-forecast-slot",
  });

  protected createRenderRoot() {
    return this;
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    this._chart?.destroy();
    this._chart = null;
  }

  protected firstUpdated(): void {
    if (this.config?.forecast?.default_chart_attribute) {
      this._selectedAttribute = this.config.forecast.default_chart_attribute;
    }
    this.initChart();
  }

  protected updated(changedProps: PropertyValues): void {
    super.updated(changedProps);
    const hasChanged =
      changedProps.has("forecast") || changedProps.has("weatherEntity") ||
      changedProps.has("hass") || changedProps.has("forecastType") || changedProps.has("itemWidth");

    if (hasChanged && this.itemWidth > 0 && this.forecast?.length) {
      if (!this._chart) {
        this.initChart();
      } else {
        const structuralChange = changedProps.has("forecastType") || changedProps.has("itemWidth");
        this.updateChartData(structuralChange);
      }
    }
  }

  render(): TemplateResult | typeof nothing {
    const forecast = this.safeForecast;
    if (!forecast?.length || this.itemWidth <= 0) return nothing;

    const count = forecast.length;
    const gaps = Math.max(count - 1, 0);
    const fontSize = this._getChartFontSize();
    const chartHeight = DEFAULT_CHART_HEIGHT + Math.max(0, fontSize - DEFAULT_CHART_FONT_SIZE);
    const totalWidthCalc = `calc(${count} * var(--forecast-item-width) + ${gaps} * var(--forecast-item-gap))`;

    return html`
      <div class="${classMap({
        "wfc-forecast-chart-settings": true,
        "has-selector": !!this.config.forecast?.show_attribute_selector,
      })}">
        ${this.config.forecast?.show_attribute_selector
          ? html`<span>${this._localizeSelectedAttribute()}</span>
              <div class="wfc-forecast-chart-attribute-selector">
                <ha-button class="wfc-settings-toggle-button" size="small" appearance="filled" variant="brand"
                  @click=${this._onSettingsToggle}>
                  <ha-icon .icon=${this._settingsOpen ? "mdi:close"
                    : this._selectedAttribute === "temperature_and_precipitation" ? "mdi:water-thermometer"
                    : WEATHER_ATTRIBUTE_ICON_MAP[this._selectedAttribute as keyof typeof WEATHER_ATTRIBUTE_ICON_MAP]}>
                  </ha-icon>
                </ha-button>
              </div>`
          : nothing}
        <wfc-chart-attribute-selector
          .open=${this._settingsOpen}
          .options=${this._getChartOptions()}
          .value=${this._selectedAttribute}
          @selected=${this._onAttributesSelected}
          @closed=${this._onSettingsClosed}
        ></wfc-chart-attribute-selector>
      </div>
      <div class="${classMap({ "wfc-mask-container": true, "is-scrollable": this.isScrollable })}">
        <div class="wfc-scroll-container"
          style=${styleMap({ "--wfc-forecast-chart-width": totalWidthCalc })}
          .actionHandler=${actionHandler({
            hasHold: this.config.forecast_action?.hold_action !== undefined,
            hasDoubleClick: this.config.forecast_action?.double_tap_action !== undefined,
            stopPropagation: true,
          })}
          @pointerdown=${this._onPointerDown}
          @action=${this._onForecastAction}>
          <div class="wfc-forecast-chart-header">${this.renderHeaderItems(forecast)}</div>
          <div class="wfc-chart-clipper" style=${styleMap({
            width: "var(--wfc-forecast-chart-width)", overflow: "hidden",
          })}>
            <div class="wfc-forecast-chart" id="chart-container" style=${styleMap({
              width: "calc(var(--wfc-forecast-chart-width) + var(--forecast-item-gap))",
              marginLeft: "calc(var(--forecast-item-gap) / -2)",
              display: "block", height: `${chartHeight}px`,
            })}>
              <canvas id="forecast-canvas"></canvas>
            </div>
          </div>
          <div class="wfc-forecast-chart-footer">
            ${forecast.map((item, index) => html`
              <div class="wfc-forecast-slot" data-index=${index}>
                <wfc-forecast-info .hass=${this.hass} .weatherEntity=${this.weatherEntity}
                  .forecast=${item} .config=${this.config} .hidePrecipitation=${true}>
                </wfc-forecast-info>
              </div>`
            )}
          </div>
        </div>
      </div>
    `;
  }

  // --- Chart Lifecycle ---

  private _getBuildContext(): ChartBuildContext {
    return {
      hass: this.hass,
      weatherEntity: this.weatherEntity,
      config: this.config,
      forecastType: this.forecastType,
      selectedAttribute: this._selectedAttribute,
      fontSize: this._getChartFontSize(),
      style: getComputedStyle(this),
    };
  }

  private _getChartConfig(): ChartConfiguration {
    return buildChartConfig(
      this._getBuildContext(),
      this.safeForecast,
      this._temperatureColors,
      (colors) => { this._temperatureColors = colors; }
    );
  }

  private initChart(): void {
    if (!this._canvas || !this.forecast?.length) return;
    const config = this._getChartConfig();
    if (config) this._chart = new Chart(this._canvas, config);
  }

  private updateChartData(structuralChange: boolean = false): void {
    if (!this._chart || !this.forecast?.length) return;
    const newConfig = this._getChartConfig();
    const currentType = (this._chart.config as ChartConfiguration).type;

    if (currentType !== newConfig.type) {
      this._chart.destroy();
      this._chart = null;
      this.initChart();
      return;
    }

    this._chart.data = newConfig.data;
    if (this._chart.options.scales && newConfig.options?.scales) {
      this._chart.options.scales = newConfig.options.scales;
    }
    if (structuralChange) this._chart.resize();
    this._chart.update("none");
  }

  private _getChartFontSize(): number {
    const style = getComputedStyle(this);
    const fontSizeStyle = style.getPropertyValue("--wfc-chart-font-size");
    if (fontSizeStyle) {
      const parsed = parseFloat(fontSizeStyle);
      if (!isNaN(parsed)) return parsed;
    }
    return DEFAULT_CHART_FONT_SIZE;
  }

  // --- Header Items ---

  private renderHeaderItems(forecast: ForecastAttribute[]): TemplateResult[] {
    const parts: TemplateResult[] = [];
    let currentDay: string | undefined;

    forecast.forEach((item, index) => {
      if (!item.datetime) return;
      if (this.forecastType === "hourly") {
        const forecastDay = formatDay(this.hass, item.datetime);
        if (currentDay !== forecastDay) {
          currentDay = forecastDay;
          parts.push(html`<div class="wfc-day-indicator-container">
            <div class="wfc-day-indicator wfc-label">${forecastDay}</div>
          </div>`);
        }
      }
      parts.push(html`
        <div class="wfc-forecast-slot" data-index=${index}>
          <wfc-forecast-header-items .hass=${this.hass} .forecast=${item}
            .forecastType=${this.forecastType} .isTwiceDailyEntity=${this.isTwiceDailyEntity}
            .config=${this.config}>
          </wfc-forecast-header-items>
        </div>`);
    });

    return parts;
  }

  // --- Safe Forecast (canvas limit) ---

  private get safeForecast(): ForecastAttribute[] {
    if (!this.forecast?.length || this.itemWidth <= 0) return [];
    const gap = parseFloat(getComputedStyle(this).getPropertyValue("--forecast-item-gap").trim()) || 0;
    const maxItems = Math.floor((MAX_CANVAS_WIDTH + gap) / (this.itemWidth + gap));
    if (this.forecast.length > maxItems) {
      logger.debug(`Truncating forecast to ${maxItems} items to stay under ${MAX_CANVAS_WIDTH}px.`);
      return this.forecast.slice(0, maxItems);
    }
    return this.forecast;
  }

  // --- Event Handlers ---

  private _onPointerDown(event: PointerEvent) {
    this._lastChartEvent = event;
  }

  private _onForecastAction = (event: ActionHandlerEvent): void => {
    if (this._scrollController.isScrolling()) return;

    if (
      this.config.forecast_action?.hold_action?.action === "select-forecast-attribute" &&
      event.detail.action === "hold"
    ) {
      event.preventDefault();
      event.stopPropagation();
      this._settingsOpen = true;
      return;
    }

    if (!this._chart || !this._lastChartEvent) return;
    const lastChartEvent = this._lastChartEvent;
    this._lastChartEvent = null;
    event.preventDefault();
    event.stopPropagation();

    const canvasPosition = getRelativePosition(lastChartEvent, this._chart);
    const xScale = this._chart.scales.x;
    if (!xScale) return;
    const dataX = xScale.getValueForPixel(canvasPosition.x);
    if (dataX == null) return;
    const label = xScale.getLabelForValue(dataX);
    const index = this._chart.data.labels?.indexOf(label as string) ?? -1;
    if (index === -1) return;

    const selectedForecast = this.safeForecast[index];
    if (!selectedForecast) return;

    fireEvent(this, "action", { selectedForecast, action: event.detail.action } as ForecastActionDetails);
  };

  private _onSettingsToggle(event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this._settingsOpen = !this._settingsOpen;
  }

  private _localizeSelectedAttribute(): string {
    if (this._selectedAttribute === "temperature_and_precipitation") {
      return this.hass.localize("ui.card.weather.forecast");
    }
    return (
      this.hass.formatEntityAttributeName(this.weatherEntity, this._selectedAttribute) ||
      this.hass.localize("ui.card.weather.forecast")
    );
  }

  private _getChartOptions(): { label: string; value: ChartAttributes; icon: string }[] {
    const hasData = (attr: string): boolean => {
      if (attr === "temperature_and_precipitation") return true;
      return this.forecast.some((f) => f[attr as keyof ForecastAttribute] != null);
    };

    return CHART_ATTRIBUTES.filter(hasData).map((attr) => ({
      label: attr === "temperature_and_precipitation"
        ? `${this.hass.formatEntityAttributeName(this.weatherEntity, "temperature")}, ${this.hass.localize("ui.card.weather.attributes.precipitation")}`
        : this.hass.formatEntityAttributeName(this.weatherEntity, attr) || attr,
      icon: attr === "temperature_and_precipitation"
        ? "mdi:water-thermometer"
        : WEATHER_ATTRIBUTE_ICON_MAP[attr as CurrentWeatherAttributes],
      value: attr,
    }));
  }

  private _onAttributesSelected(e: CustomEvent): void {
    this._settingsOpen = false;
    this._selectedAttribute = e.detail.value;
    this.updateChartData(false);
  }

  private _onSettingsClosed(): void {
    this._settingsOpen = false;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "wfc-forecast-chart": WfcForecastChart;
  }
}
