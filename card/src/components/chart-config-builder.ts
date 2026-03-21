import {
  ChartConfiguration,
  ChartDataset,
  ChartOptions,
  Color,
  ScriptableContext,
} from "chart.js";
import { deepMerge } from "../helpers";
import {
  ForecastAttribute,
  ForecastType,
  formatPrecipitation,
  formatTemperature,
  getMaxPrecipitationForUnit,
  getWeatherUnit,
  WeatherEntity,
} from "../data/weather";
import {
  ChartAttributes,
  ExtendedHomeAssistant,
  WeatherForecastCardConfig,
} from "../types";

type ForecastLineType = "temperature" | "templow";
type ForecastLineStyle = Pick<
  ChartDataset<"line">,
  "borderColor" | "pointBackgroundColor" | "pointBorderColor" | "fill" | "borderDash"
>;

const DEFAULT_CHART_FONT_SIZE = 12;
const DEFAULT_CHART_PADDING = 10;
const MIN_RENDER_EVERY_SECOND_LABEL = 6;

export { DEFAULT_CHART_FONT_SIZE, WEATHER_ATTRIBUTE_ICON_MAP };

export interface ChartBuildContext {
  hass: ExtendedHomeAssistant;
  weatherEntity: WeatherEntity;
  config: WeatherForecastCardConfig;
  forecastType: ForecastType;
  selectedAttribute: ChartAttributes;
  fontSize: number;
  style: CSSStyleDeclaration;
}

// --- Base Options ---

export function buildBaseOptions(ctx: ChartBuildContext): ChartOptions {
  const gridColor = ctx.style.getPropertyValue("--wfc-chart-grid-color");
  const bottomPadding = DEFAULT_CHART_PADDING + (ctx.fontSize - DEFAULT_CHART_FONT_SIZE);

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      datalabels: { font: { size: ctx.fontSize } },
    },
    layout: {
      autoPadding: false,
      padding: { top: DEFAULT_CHART_PADDING, bottom: bottomPadding, left: 0, right: 0 },
    },
    elements: { line: { tension: 0.3 } },
    scales: {
      x: {
        offset: true,
        border: { color: gridColor, dash: [4, 4] },
        grid: { offset: true, display: true, color: gridColor, drawTicks: true },
        ticks: { display: false },
      },
    },
  };
}

// --- Config Dispatching ---

export function buildChartConfig(
  ctx: ChartBuildContext,
  data: ForecastAttribute[],
  temperatureColors: Record<string, string> | null,
  onColorsResolved: (colors: Record<string, string>) => void
): ChartConfiguration {
  const baseOptions = buildBaseOptions(ctx);

  switch (ctx.selectedAttribute) {
    case "uv_index":
      return buildUVIndexConfig(ctx, data, baseOptions);
    case "humidity":
    case "pressure":
    case "apparent_temperature":
      return buildAttributeConfig(ctx, data, baseOptions);
    case "temperature_and_precipitation":
    default:
      return buildDefaultWeatherConfig(ctx, data, baseOptions, temperatureColors, onColorsResolved);
  }
}

// --- Default Weather (temp + precip) ---

function buildDefaultWeatherConfig(
  ctx: ChartBuildContext,
  data: ForecastAttribute[],
  options: ChartOptions,
  temperatureColors: Record<string, string> | null,
  onColorsResolved: (colors: Record<string, string>) => void
): ChartConfiguration {
  const { style, hass, weatherEntity, config } = ctx;
  const { minTemp, maxTemp } = computeScaleLimits(data);
  const highTempLabelColor = style.getPropertyValue("--wfc-chart-temp-high-label-color");
  const lowTempLabelColor = style.getPropertyValue("--wfc-chart-temp-low-label-color");
  const precipLabelColor = style.getPropertyValue("--wfc-chart-precipitation-label-color");
  const precipColor = style.getPropertyValue("--wfc-precipitation-bar-color");

  const maxPrecip = getMaxPrecipitationForUnit(
    getWeatherUnit(hass, weatherEntity, "precipitation"),
    ctx.forecastType
  );
  const barLabelOffset = getBarLabelOffset(ctx.fontSize);
  const precision = config.forecast?.temperature_precision;

  const tempLineStyle = getTemperatureLineStyle(
    style, "temperature", config, temperatureColors, onColorsResolved, hass, weatherEntity
  );
  const templowLineStyle = getTemperatureLineStyle(
    style, "templow", config, temperatureColors, onColorsResolved, hass, weatherEntity
  );

  return {
    type: "line",
    data: {
      labels: data.map((f) => f.datetime),
      datasets: [
        {
          data: data.map((f) => f.temperature),
          yAxisID: "yTemp",
          datalabels: {
            anchor: "end", align: "top", color: highTempLabelColor,
            formatter: (value) => value != null
              ? `${formatTemperature(hass, weatherEntity, value, precision, true)}°` : null,
          },
          ...tempLineStyle,
        },
        {
          data: data.map((f) => f.templow ?? null),
          yAxisID: "yTemp",
          datalabels: {
            anchor: "start", align: "bottom", color: lowTempLabelColor,
            formatter: (value) => value != null
              ? `${formatTemperature(hass, weatherEntity, value, precision, true)}°` : null,
          },
          ...templowLineStyle,
        },
        {
          type: "bar",
          data: data.map((f) => f.precipitation && f.precipitation !== 0 ? f.precipitation : null),
          backgroundColor: precipColor,
          yAxisID: "yPrecip",
          borderWidth: 0,
          borderRadius: { topLeft: 3, topRight: 3 },
          categoryPercentage: 0.6, barPercentage: 0.8, order: 0,
          datalabels: {
            anchor: "start", align: "end", offset: barLabelOffset, color: precipLabelColor,
            formatter: (value: number) =>
              formatPrecipitation(value, getWeatherUnit(hass, weatherEntity, "precipitation")),
          },
        },
      ],
    },
    options: deepMerge({}, options, {
      scales: {
        yTemp: {
          type: "linear", display: false, min: minTemp, max: maxTemp, position: "left",
          grid: { display: false }, ticks: { display: false },
        },
        yPrecip: {
          type: "linear", display: false, position: "right", beginAtZero: true,
          suggestedMin: 0, suggestedMax: maxPrecip,
          grid: { display: false, drawOnChartArea: false }, ticks: { display: false },
        },
      },
    }),
  };
}

// --- UV Index ---

function buildUVIndexConfig(
  ctx: ChartBuildContext,
  data: ForecastAttribute[],
  options: ChartOptions
): ChartConfiguration {
  const { style } = ctx;
  const defaultColor = style.getPropertyValue("--wfc-chart-uv-bar-color").trim();
  const labelColor = style.getPropertyValue("--wfc-chart-label-color");

  const uvColors = {
    low: style.getPropertyValue("--wfc-uv-low").trim(),
    moderate: style.getPropertyValue("--wfc-uv-moderate").trim(),
    high: style.getPropertyValue("--wfc-uv-high").trim(),
    veryHigh: style.getPropertyValue("--wfc-uv-very-high").trim(),
    extreme: style.getPropertyValue("--wfc-uv-extreme").trim(),
  };

  const getUvColor = (value: number | null) => {
    if (value === null) return defaultColor;
    if (value >= 11) return uvColors.extreme;
    if (value >= 8) return uvColors.veryHigh;
    if (value >= 6) return uvColors.high;
    if (value >= 3) return uvColors.moderate;
    return uvColors.low;
  };

  return {
    type: "bar",
    data: {
      labels: data.map((f) => f.datetime),
      datasets: [{
        type: "bar",
        data: data.map((f) => f.uv_index != null ? Math.round(f.uv_index) : 0),
        backgroundColor: data.map((f) => getUvColor(f.uv_index ?? null)),
        borderWidth: 0,
        borderRadius: { topLeft: 5, topRight: 5 },
        categoryPercentage: 0.6, barPercentage: 0.8, order: 0,
        datalabels: {
          anchor: "start", align: "end",
          offset: getBarLabelOffset(ctx.fontSize), color: labelColor,
        },
      }],
    },
    options: deepMerge({}, options, {
      scales: { y: { display: false, beginAtZero: true, suggestedMax: 11 } },
    }),
  };
}

// --- Generic Attribute (humidity, pressure, apparent_temperature) ---

function buildAttributeConfig(
  ctx: ChartBuildContext,
  data: ForecastAttribute[],
  options: ChartOptions
): ChartConfiguration {
  const { style, hass, weatherEntity } = ctx;
  const attr = ctx.selectedAttribute as keyof ForecastAttribute;
  const colorVar =
    attr === "humidity" ? "--wfc-chart-humidity-line-color"
    : attr === "pressure" ? "--wfc-chart-pressure-line-color"
    : "--wfc-chart-temp-high-line-color";

  const color = style.getPropertyValue(colorVar) || style.getPropertyValue("--wfc-chart-default-line-color");
  const labelColor = style.getPropertyValue("--wfc-chart-label-color");
  const unit = getWeatherUnit(hass, weatherEntity, attr);

  const values = data.map((f) => (f[attr] as number) ?? 0);
  const dataMax = Math.max(...values);
  const dataMin = Math.min(...values);
  const range = dataMax - dataMin || 1;

  return {
    type: "line",
    data: {
      labels: data.map((f) => f.datetime),
      datasets: [{
        data: data.map((f) => (f[attr] as number) ?? null),
        borderColor: color, pointBackgroundColor: color, fill: false,
        datalabels: {
          anchor: "end", align: "top", color: labelColor,
          formatter: (value: number | null, context) => {
            if (value === null) return null;
            const formatted = `${value} ${unit}`;
            if (formatted.length > MIN_RENDER_EVERY_SECOND_LABEL && context.dataIndex % 2 !== 0) return null;
            return formatted;
          },
        },
      }],
    },
    options: deepMerge({}, options, {
      scales: { y: { display: false, min: dataMin - range * 0.1, max: dataMax + range * 0.2 } },
    }),
  };
}

// --- Temperature Line Styling ---

function getTemperatureLineStyle(
  style: CSSStyleDeclaration,
  type: ForecastLineType,
  config: WeatherForecastCardConfig,
  temperatureColors: Record<string, string> | null,
  onColorsResolved: (colors: Record<string, string>) => void,
  hass: ExtendedHomeAssistant,
  weatherEntity: WeatherEntity,
): ForecastLineStyle {
  const colorVarName = type === "temperature"
    ? "--wfc-chart-temp-high-line-color"
    : "--wfc-chart-temp-low-line-color";
  const defaultColor = style.getPropertyValue(colorVarName);

  const lineColor = (context: ScriptableContext<"line">) =>
    computeTemperatureLineColor(context, style, defaultColor, config, temperatureColors, onColorsResolved, hass, weatherEntity);

  return {
    borderColor: lineColor,
    pointBorderColor: lineColor,
    pointBackgroundColor: lineColor,
    borderDash: config.forecast?.use_color_thresholds && type === "templow" ? [4, 4] : undefined,
    fill: false,
  };
}

// --- Temperature Gradient ---

function computeTemperatureLineColor(
  context: ScriptableContext<"line">,
  componentStyle: CSSStyleDeclaration,
  defaultColor: string,
  config: WeatherForecastCardConfig,
  temperatureColors: Record<string, string> | null,
  onColorsResolved: (colors: Record<string, string>) => void,
  hass: ExtendedHomeAssistant,
  weatherEntity: WeatherEntity,
): CanvasGradient | Color {
  if (!config.forecast?.use_color_thresholds) return defaultColor;

  const { ctx, chartArea, scales } = context.chart;
  if (!chartArea || !scales.yTemp) return defaultColor;

  if (!temperatureColors) {
    const resolved = {
      cold: componentStyle.getPropertyValue("--wfc-temp-cold") || "#2196f3",
      freezing: componentStyle.getPropertyValue("--wfc-temp-freezing") || "#4fb3ff",
      chilly: componentStyle.getPropertyValue("--wfc-temp-chilly") || "#ffeb3b",
      mild: componentStyle.getPropertyValue("--wfc-temp-mild") || "#4caf50",
      warm: componentStyle.getPropertyValue("--wfc-temp-warm") || "#ff9800",
      hot: componentStyle.getPropertyValue("--wfc-temp-hot") || "#f44336",
    };
    onColorsResolved(resolved);
    temperatureColors = resolved;
  }

  const { min, max } = scales.yTemp;
  if (!Number.isFinite(min) || !Number.isFinite(max)) return defaultColor;

  const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
  const getPos = (temp: number) => Math.max(0, Math.min(1, (temp - min) / (max - min)));

  const unit = getWeatherUnit(hass, weatherEntity, "temperature");
  const normalize = unit === "°F" ? (c: number) => (c * 9) / 5 + 32 : (c: number) => c;

  const stops = [
    { pos: getPos(normalize(-10)), color: temperatureColors.cold },
    { pos: getPos(normalize(0)), color: temperatureColors.freezing },
    { pos: getPos(normalize(8)), color: temperatureColors.chilly },
    { pos: getPos(normalize(18)), color: temperatureColors.mild },
    { pos: getPos(normalize(26)), color: temperatureColors.warm },
    { pos: getPos(normalize(34)), color: temperatureColors.hot },
  ].sort((a, b) => a.pos - b.pos);

  for (const stop of stops) {
    gradient.addColorStop(stop.pos, stop.color!);
  }

  return gradient;
}

// --- Scale Limits ---

export function computeScaleLimits(forecast: ForecastAttribute[]): { minTemp: number; maxTemp: number } {
  const temps = forecast.map((f) => f.temperature);
  const lows = forecast.map((f) => f.templow ?? f.temperature);

  const dataMin = Math.min(...lows);
  const dataMax = Math.max(...temps);
  const hasLowTempData = forecast.some((f) => f.templow != null);

  const spread = Math.max(dataMax - dataMin, 10);
  const topPaddingFactor = 0.2;
  const bottomPaddingFactor = hasLowTempData ? 0.35 : 0.1;

  const MIN_TOP_BUFFER = 2;
  const MIN_BOTTOM_BUFFER = hasLowTempData ? 5 : 1;

  const topPadding = Math.max(spread * topPaddingFactor, MIN_TOP_BUFFER);
  const bottomPadding = Math.max(spread * bottomPaddingFactor, MIN_BOTTOM_BUFFER);

  const minTemp = Math.floor(dataMin - bottomPadding);
  let maxTemp = Math.ceil(dataMax + topPadding);
  if (minTemp >= maxTemp) maxTemp = minTemp + 1;

  return { minTemp, maxTemp };
}

// --- Helpers ---

export function getBarLabelOffset(fontSize: number): number {
  return -22 - (fontSize - DEFAULT_CHART_FONT_SIZE);
}
