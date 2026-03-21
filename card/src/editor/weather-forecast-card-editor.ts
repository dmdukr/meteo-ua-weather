/* eslint-disable @typescript-eslint/no-empty-object-type */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { LitElement, html, TemplateResult, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import memoizeOne from "memoize-one";
import { capitalize } from "../helpers";
import {
  fireEvent,
  LovelaceCardEditor,
  LocalizeFunc,
} from "custom-card-helpers";
import {
  CHART_ATTRIBUTES,
  CURRENT_WEATHER_ATTRIBUTES,
  CurrentWeatherAttributes,
  CurrentWeatherAttributeConfig,
  ExtendedHomeAssistant,
  MAX_TEMPERATURE_PRECISION,
  WEATHER_EFFECTS,
  WeatherForecastCardConfig,
  WeatherForecastCardCurrentConfig,
  WeatherForecastCardForecastActionConfig,
  WeatherForecastCardForecastConfig,
  WeatherForecastCardMonthlyGridConfig,
} from "../types";

// Device class mapping for attribute entity selectors
const ATTRIBUTE_DEVICE_CLASS_MAP: Record<
  CurrentWeatherAttributes,
  string | string[] | undefined
> = {
  humidity: "humidity",
  pressure: ["pressure", "atmospheric_pressure"],
  wind_speed: "wind_speed",
  wind_gust_speed: "wind_speed",
  visibility: "distance",
  dew_point: "temperature",
  apparent_temperature: "temperature",
  uv_index: undefined, // any sensor
  ozone: undefined, // any sensor
  cloud_coverage: undefined, // any sensor
};

type HaFormSelector =
  | { entity: { domain?: string; device_class?: string | string[] } }
  | { boolean: {} }
  | { text: {} }
  | { entity_name: {} }
  | { number: { min?: number; max?: number } }
  | { ui_action: { default_action: string } }
  | {
      select: {
        mode?: "dropdown" | "list";
        options: Array<{ value: string; label: string }>;
        custom_value?: boolean;
        multiple?: boolean;
      };
    };

type HaFormSchema = {
  name:
    | keyof WeatherForecastCardEditorConfig
    | `forecast.${keyof WeatherForecastCardForecastConfig}`
    | `current.${keyof WeatherForecastCardCurrentConfig}`
    | `forecast_action.${keyof WeatherForecastCardForecastActionConfig}`
    | `monthly_grid.${keyof WeatherForecastCardMonthlyGridConfig}`
    | `current.attribute_entity_${CurrentWeatherAttributes}`
    | "attribute_entities"
    | "hourly_forecast_settings"
    | "daily_forecast_settings"
    | "monthly_forecast_settings"
    | "";
  type?: string;
  iconPath?: TemplateResult;
  schema?: HaFormSchema[];
  flatten?: boolean;
  default?: string | boolean | number;
  required?: boolean;
  selector?: HaFormSelector;
  context?: { entity?: string };
  optional?: boolean;
  disabled?: boolean;
};

type WeatherForecastCardEditorConfig = {
  forecast_mode?: "show_both" | "show_current" | "show_forecast";
  forecast_interactions?: unknown;
  interactions?: unknown;
  advanced_settings?: unknown;
} & WeatherForecastCardConfig;

@customElement("meteo-ua-weather-forecast-card-editor")
export class WeatherForecastCardEditor
  extends LitElement
  implements LovelaceCardEditor
{
  @property({ attribute: false }) public hass!: ExtendedHomeAssistant;
  @state() private _config!: WeatherForecastCardEditorConfig;

  public setConfig(config: WeatherForecastCardEditorConfig): void {
    this._config = config;
  }

  private _uk(): boolean {
    return this.hass?.language === "uk";
  }

  private _effectLabel = (effect: string): string => {
    const uk: Record<string, string> = {
      rain: "Дощ", snow: "Сніг", lightning: "Блискавка",
      sky: "Небо", moon: "Місяць", sun: "Сонце",
      clouds: "Хмари", partlyclouds: "Мінлива хмарність",
      fog: "Туман", hail: "Град", wind: "Вітер",
      warning: "Попередження",
    };
    return (this.hass?.language === "uk" ? uk[effect] : undefined) ?? capitalize(effect);
  };

  private _t(uk: string, en: string): string {
    return this._uk() ? uk : en;
  }

  private _schema = memoizeOne(
    (
      mode?: string,
    ): HaFormSchema[] =>
      [
        ...this._genericSchema(),
        ...this._currentWeatherSchema(this.localize.bind(this)),
        ...this._forecastSchema(this.localize.bind(this)),
        ...this._monthlyGridSchema(),
        ...this._interactionsSchema(mode),
        ...this._generalSettingsSchema(),
      ] as const
  );

  private _genericSchema = (): HaFormSchema[] =>
    [
      {
        name: "entity",
        required: true,
        selector: { entity: { domain: "weather" } },
        optional: false,
      },
      {
        name: "name",
        selector: { text: {} },
        optional: true,
      },
      {
        name: "show_condition_effects",
        default: false,
        optional: true,
        selector: {
          select: {
            multiple: true,
            options: WEATHER_EFFECTS.map((effect) => ({
              value: effect,
              label: this._effectLabel(effect),
            })),
          },
        },
      },
    ] as const;

  private _currentWeatherSchema = (localize: LocalizeFunc): HaFormSchema[] =>
    [
      {
        name: "current.temperature_entity",
        selector: {
          entity: { domain: "sensor", device_class: "temperature" },
        },
        optional: true,
      },
      {
        name: "current.show_attributes",
        default: false,
        optional: true,
        selector: {
          select: {
            multiple: true,
            options: CURRENT_WEATHER_ATTRIBUTES.map((attribute) => ({
              value: attribute,
              label:
                localize(`ui.card.weather.attributes.${attribute}`) ||
                capitalize(attribute).replace(/_/g, " "),
            })),
          },
        },
      },
      {
        name: "current.secondary_info_attribute",
        default: "none",
        optional: true,
        selector: {
          select: {
            options: CURRENT_WEATHER_ATTRIBUTES.map((attribute) => ({
              value: attribute,
              label:
                localize(`ui.card.weather.attributes.${attribute}`) ||
                capitalize(attribute).replace(/_/g, " "),
            })),
          },
        },
      },
      {
        name: "current.temperature_precision",
        optional: true,
        selector: { number: { min: 0, max: MAX_TEMPERATURE_PRECISION } },
      },
    ] as const;

  private _forecastSchema = (localize: LocalizeFunc): HaFormSchema[] =>
    [
      { name: "forecast.scroll_to_selected", selector: { boolean: {} }, default: true, optional: true },
      { name: "forecast.use_color_thresholds", selector: { boolean: {} }, default: true, optional: true },
      {
        name: "forecast.extra_attribute", optional: true,
        selector: { select: { mode: "dropdown", options: [
          { value: "none", label: localize("ui.panel.lovelace.editor.card.weather-forecast.none") || "(no attribute)" },
          { value: "wind_bearing", label: localize("ui.card.weather.attributes.wind_bearing") || "Wind bearing" },
          { value: "wind_direction", label: localize("ui.card.weather.attributes.wind_direction") || "Wind direction" },
          { value: "precipitation_probability", label: localize("ui.card.weather.attributes.precipitation_probability") || "Precipitation probability" },
        ] } },
      },
      {
        name: "hourly_forecast_settings", type: "expandable", flatten: true,
        schema: [
          { name: "show_hourly_forecast", selector: { boolean: {} }, default: true, optional: true },
          {
            name: "forecast.mode", default: "simple", optional: true,
            selector: { select: { options: [
              { value: "simple", label: this._t("Простий", "Simple") },
              { value: "chart", label: this._t("Графік", "Chart") },
            ] } },
          },
          {
            name: "forecast.default_chart_attribute", optional: true,
            selector: { select: { mode: "dropdown", options: CHART_ATTRIBUTES.map((attribute) => ({
              value: attribute,
              label: attribute === "temperature_and_precipitation"
                ? `${localize("ui.card.weather.attributes.temperature") || "Temperature"}, ${localize("ui.card.weather.attributes.precipitation") || "Precipitation"}`
                : localize(`ui.card.weather.attributes.${attribute}`) || capitalize(attribute).replace(/_/g, " "),
            })) } },
          },
          { name: "forecast.show_attribute_selector", selector: { boolean: {} }, default: false, optional: true },
          { name: "forecast.show_sun_times", selector: { boolean: {} }, default: true, optional: true },
          { name: "forecast.hourly_group_size", optional: true, selector: { number: { min: 1, max: 4 } }, default: 1 },
          { name: "forecast.hourly_slots", optional: true, selector: { number: { min: 1 } } },
          { name: "forecast.temperature_precision", optional: true, selector: { number: { min: 0, max: MAX_TEMPERATURE_PRECISION } } },
        ],
      },
      {
        name: "daily_forecast_settings", type: "expandable", flatten: true,
        schema: [
          { name: "show_daily_forecast", selector: { boolean: {} }, default: true, optional: true },
          { name: "forecast.daily_slots", optional: true, selector: { number: { min: 1 } }, default: 30 },
          { name: "forecast.daily_columns", optional: true, selector: { number: { min: 1, max: 10 } }, default: 6 },
        ],
      },
    ] as const;

  private _monthlyGridSchema = (): HaFormSchema[] =>
    [
      {
        name: "monthly_forecast_settings",
        type: "expandable",
        flatten: true,
        schema: [
          { name: "monthly_grid.show", selector: { boolean: {} }, default: true, optional: true },
          { name: "monthly_grid.columns", optional: true, selector: { number: { min: 2, max: 10 } }, default: 6 },
          { name: "monthly_grid.show_wind", selector: { boolean: {} }, default: true, optional: true },
          { name: "monthly_grid.show_chart", selector: { boolean: {} }, default: true, optional: true },
          { name: "monthly_grid.compact", selector: { boolean: {} }, default: false, optional: true },
        ],
      },
    ] as const;

  private _interactionsSchema = (mode?: string): HaFormSchema[] => {
    const optionalActions: (keyof WeatherForecastCardForecastActionConfig)[] =
      [];
    const forecastActionSchema: HaFormSchema[] = [
      {
        name: "forecast_action.tap_action",
        selector: {
          ui_action: {
            default_action: "toggle-forecast",
          },
        },
      },
    ];

    if (mode === "chart") {
      optionalActions.push("double_tap_action");
      forecastActionSchema.push({
        name: "forecast_action.hold_action",
        selector: {
          ui_action: {
            default_action: "select-forecast-attribute",
          },
        },
      });
    } else {
      optionalActions.push("hold_action", "double_tap_action");
    }

    forecastActionSchema.push({
      name: "",
      type: "optional_actions",
      flatten: true,
      schema: optionalActions.map((action) => ({
        name: `forecast_action.${action}` as const,
        selector: {
          ui_action: {
            default_action: "none" as const,
          },
        },
      })),
    });

    return [
      {
        name: "forecast_interactions",
        type: "expandable",
        flatten: true,
        schema: forecastActionSchema,
      },
      {
        name: "interactions",
        type: "expandable",
        flatten: true,
        schema: [
          {
            name: "tap_action",
            selector: {
              ui_action: {
                default_action: "more-info",
              },
            },
          },
          {
            name: "",
            type: "optional_actions",
            flatten: true,
            schema: (["hold_action", "double_tap_action"] as const).map(
              (action) => ({
                name: action,
                selector: {
                  ui_action: {
                    default_action: "none" as const,
                  },
                },
              })
            ),
          },
        ],
      },
    ] as const;
  };

  private _attributeEntitiesSchema = (
    selectedAttributes: CurrentWeatherAttributes[]
  ): HaFormSchema[] => {
    if (selectedAttributes.length === 0) {
      return [];
    }

    const attributeEntitySchemas: HaFormSchema[] = selectedAttributes.map(
      (attribute) => {
        const deviceClass = ATTRIBUTE_DEVICE_CLASS_MAP[attribute];
        return {
          name: `current.attribute_entity_${attribute}`,
          optional: true,
          selector: deviceClass
            ? { entity: { domain: "sensor", device_class: deviceClass } }
            : { entity: { domain: "sensor" } },
        };
      }
    );

    return [
      {
        name: "attribute_entities",
        type: "expandable",
        flatten: true,
        schema: attributeEntitySchemas,
      },
    ];
  };

  private _generalSettingsSchema = (): HaFormSchema[] =>
    [
      ...this._attributeEntitiesSchema(this._getSelectedAttributes(denormalizeConfig(this._config))),
      {
        name: "advanced_settings",
        type: "expandable",
        flatten: true,
        schema: [
          {
            name: "icons_path",
            selector: { text: {} },
            optional: true,
          },
        ],
      },
    ] as const;

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) {
      return nothing;
    }

    const data = denormalizeConfig(this._config);
    const schema = this._schema(
      data["forecast.mode"],
    );

    return html`
      <ha-form
        .hass=${this.hass}
        .data=${data}
        .schema=${schema}
        .computeLabel=${this._computeLabel}
        .computeHelper=${this._computeHelper}
        @value-changed=${this._valueChanged}
      >
      </ha-form>
    `;
  }

  private _getSelectedAttributes(
    data: Record<string, any>
  ): CurrentWeatherAttributes[] {
    const showAttributes = data["current.show_attributes"];

    if (!showAttributes) {
      return [];
    }

    if (Array.isArray(showAttributes)) {
      // Handle mixed array of strings and objects
      return showAttributes.map(
        (item: string | CurrentWeatherAttributeConfig) =>
          (typeof item === "string"
            ? item
            : item.name) as CurrentWeatherAttributes
      );
    }

    return [];
  }

  private _computeLabel = (schema: HaFormSchema): string | undefined => {
    if (schema.name.startsWith("current.attribute_entity_")) {
      const attribute = schema.name.replace("current.attribute_entity_", "");
      const attributeLabel =
        this.localize(`ui.card.weather.attributes.${attribute}`) ||
        capitalize(attribute).replace(/_/g, " ");
      const entityLabel = (
        this.hass!.localize("ui.panel.lovelace.editor.card.generic.entity") ||
        "entity"
      ).toLocaleLowerCase();

      return `${attributeLabel} ${entityLabel}`;
    }

    const name = schema.name.startsWith("forecast_action.")
      ? schema.name.split(".")[1]
      : schema.name;

    switch (name) {
      case "hourly_forecast_settings":
        return this._t("Погодинний прогноз", "Hourly forecast");
      case "daily_forecast_settings":
        return this._t("Поденний прогноз", "Daily forecast");
      case "show_hourly_forecast":
        return this._t("Показувати погодинний прогноз", "Show hourly forecast");
      case "show_daily_forecast":
        return this._t("Показувати поденний прогноз", "Show daily forecast");
      case "forecast.daily_columns":
        return this._t("Днів у рядку", "Days per row");
      case "entity":
        return `${this.hass!.localize("ui.panel.lovelace.editor.card.generic.entity")} (${(
          this.hass!.localize(
            "ui.panel.lovelace.editor.card.config.required"
          ) || "required"
        ).toLocaleLowerCase()})`;
      case "name":
        return this.hass.localize("ui.panel.lovelace.editor.card.generic.name");
      case "current.temperature_entity":
        return `${this.hass!.localize("ui.card.weather.attributes.temperature")} ${(
          this.hass!.localize("ui.panel.lovelace.editor.card.generic.entity") ||
          "entity"
        ).toLocaleLowerCase()}`;
      case "forecast_mode":
        return this.hass!.localize(
          "ui.panel.lovelace.editor.card.weather-forecast.weather_to_show"
        );
      case "icons_path":
        return this._t("Шлях до іконок", "Icons path");
      case "current.show_attributes":
        return (
          this.hass!.localize(
            "ui.panel.lovelace.editor.card.generic.attribute"
          ) || "attribute"
        );
      case "current.secondary_info_attribute":
        return (
          this.hass.localize(
            "ui.panel.lovelace.editor.card.generic.secondary_info_attribute"
          ) || "Secondary info attribute"
        );
      case "forecast.extra_attribute":
        return `Extra ${(
          this.hass!.localize("ui.card.weather.forecast") || "forecast"
        ).toLocaleLowerCase()} ${(
          this.hass!.localize(
            "ui.panel.lovelace.editor.card.generic.attribute"
          ) || "attribute"
        ).toLocaleLowerCase()}`;
      case "forecast.mode":
        return this._t("Режим відображення", "Display mode");
      case "current.temperature_precision":
        return this._t("Точність поточної t°", "Current temp precision");
      case "forecast.temperature_precision":
        return this._t("Точність t° прогнозу", "Forecast temp precision");
      case "forecast.scroll_to_selected":
        return this._t("Прокрутка до обраного", "Scroll to selected");
      case "forecast.show_sun_times":
        return this._t("Схід і захід сонця", "Sunrise/sunset");
      case "forecast.use_color_thresholds":
        return this._t("Кольорові пороги", "Color thresholds");
      case "forecast.show_attribute_selector":
        return this._t("Вибір атрибутів", "Attribute selector");
      case "forecast.default_chart_attribute":
        return this._t("Атрибут графіка", "Chart attribute");
      case "forecast.hourly_group_size":
        return this._t("Групування годин", "Hourly group size");
      case "forecast.hourly_slots":
        return this._t("Кількість годин", "Hourly slots");
      case "forecast.daily_slots":
        return this._t("Кількість днів", "Daily slots");
      case "forecast_interactions":
        return `${this.hass!.localize("ui.card.weather.forecast")} ${(
          this.hass!.localize(
            `ui.panel.lovelace.editor.card.generic.interactions`
          ) || "interactions"
        ).toLocaleLowerCase()}`;
      case "advanced_settings":
        return this.hass!.localize(
          "ui.dialogs.helper_settings.generic.advanced_settings"
        );
      case "show_condition_effects":
        return this._t("Ефекти погоди", "Condition effects");
      case "monthly_forecast_settings":
        return this._t("Місячний прогноз", "Monthly forecast");
      case "monthly_grid.show":
        return this._t("Показувати місячну сітку", "Show monthly grid");
      case "monthly_grid.columns":
        return this._t("Днів у рядку", "Days per row");
      case "monthly_grid.show_wind":
        return this._t("Показувати вітер", "Show wind");
      case "monthly_grid.show_chart":
        return this._t("Хвиля температури", "Temperature wave");
      case "monthly_grid.compact":
        return this._t("Компактний режим", "Compact mode");
      case "attribute_entities":
        return `${
          this.hass!.localize(
            "ui.panel.lovelace.editor.card.generic.attribute"
          ) || "attribute"
        } ${(this.hass!.localize("ui.panel.lovelace.editor.card.generic.entities") || "entities").toLocaleLowerCase()}`;
      default:
        return this.hass!.localize(
          `ui.panel.lovelace.editor.card.generic.${name}`
        );
    }
  };

  private _computeHelper = (schema: HaFormSchema): string | undefined => {
    switch (schema.name) {
      case "current.temperature_entity":
        return this._t("Сенсор температури.", "Temperature sensor override.");
      case "current.show_attributes":
        return this._t("Атрибути поточної погоди.", "Weather attributes to display.");
      case "current.secondary_info_attribute":
        return this._t("Додатковий атрибут.", "Secondary info attribute.");
      case "forecast.extra_attribute":
        return this._t("Додатковий атрибут прогнозу.", "Extra forecast attribute.");
      case "forecast_interactions":
        return this._t("Дія при натисканні на прогноз. За замовчуванням перемикає між погодинним і поденним.", "Action on forecast tap. Default toggles between hourly and daily.");
      case "interactions":
        return this._t("Дія при натисканні на область поза прогнозом.", "Action on non-forecast area tap.");
      case "icons_path":
        return this._t("Шлях до іконок.", "Path to custom icons.");
      case "forecast.scroll_to_selected":
        return this._t("Прокрутка до обраного.", "Scroll to selected.");
      case "forecast.show_sun_times":
        return this._t("Час сходу/заходу сонця.", "Sunrise/sunset in hourly forecast.");
      case "forecast.use_color_thresholds":
        return this._t("Градієнт температури.", "Temperature gradient.");
      case "forecast.show_attribute_selector":
        return this._t("Перемикач над графіком.", "Selector above chart.");
      case "forecast.default_chart_attribute":
        return this._t("Атрибут графіка.", "Default chart attribute.");
      case "forecast.hourly_group_size":
        return this._t("Групування годин.", "Aggregate hourly data.");
      case "forecast.hourly_slots":
        return this._t("Максимум годин.", "Max hourly entries.");
      case "forecast.daily_columns":
        return this._t("Днів в рядку.", "Days per row.");
      case "forecast.daily_slots":
        return this._t("Максимум днів.", "Max daily entries.");
      case "current.temperature_precision":
        return this._t("Десяткові знаки.", "Decimal places.");
      case "forecast.temperature_precision":
        return this._t("Десяткові знаки.", "Decimal places.");
      case "name":
        return this._t("Перевизначає імʼя сутності.", "Overrides the friendly name.");
      case "show_condition_effects":
        return this._t("Погодні умови для ефектів.", "Conditions for effects.");
      case "monthly_grid.show":
        return this._t("Сітка місячного прогнозу.", "Monthly forecast grid.");
      case "monthly_grid.columns":
        return this._t("Днів у одному рядку.", "Days per single row.");
      case "monthly_grid.show_wind":
        return this._t("Індикатор вітру.", "Wind indicator per day.");
      case "monthly_grid.show_chart":
        return this._t("SVG хвиля температури.", "SVG temperature wave.");
      case "monthly_grid.compact":
        return this._t("Менші комірки.", "Smaller cells.");
      case "attribute_entities":
        return this._t("Заміна сенсорами.", "Override with sensors.");
      default:
        return undefined;
    }
  };

  private _valueChanged(ev: CustomEvent): void {
    ev.stopPropagation();

    const config = ev.detail.value as WeatherForecastCardEditorConfig;

    config.show_current = true;
    config.show_forecast = config.show_hourly_forecast !== false || config.show_daily_forecast !== false;

    const newConfig = moveDottedKeysToNested(config);

    // Remove legacy root-level temperature_entity (now under current.temperature_entity)
    delete newConfig.temperature_entity;

    if (newConfig?.forecast?.extra_attribute === "none") {
      delete newConfig.forecast.extra_attribute;
    }

    if (Array.isArray(newConfig.show_condition_effects)) {
      const hasAll = WEATHER_EFFECTS.every((effect) =>
        newConfig.show_condition_effects.includes(effect)
      );

      if (hasAll) {
        newConfig.show_condition_effects = true;
      }
    }

    // Convert show_attributes to object format if custom entities are specified
    if (newConfig?.current) {
      const attributeEntities: Record<string, string> = {};

      for (const key of Object.keys(newConfig.current)) {
        if (key.startsWith("attribute_entity_")) {
          const attribute = key.replace(
            "attribute_entity_",
            ""
          ) as CurrentWeatherAttributes;
          const entity = newConfig.current[key];
          if (entity) {
            attributeEntities[attribute] = entity;
          }
          delete newConfig.current[key];
        }
      }

      if (Array.isArray(newConfig.current.show_attributes)) {
        const hasCustomEntities = Object.keys(attributeEntities).length > 0;
        const allSelected = CURRENT_WEATHER_ATTRIBUTES.every((attribute) =>
          newConfig.current.show_attributes.includes(attribute)
        );

        if (hasCustomEntities) {
          newConfig.current.show_attributes =
            newConfig.current.show_attributes.map((attr: string) => {
              const entity = attributeEntities[attr];
              if (entity) {
                return { name: attr, entity };
              }
              return attr;
            });
        } else if (allSelected) {
          newConfig.current.show_attributes = true;
        }
      }
    }

    fireEvent(this, "config-changed", { config: newConfig });
  }

  private localize = (key: string): string => {
    let result: string | undefined;

    if (
      this._config?.entity &&
      key !== "ui.card.weather.attributes.precipitation" && // Precipitation is not yet supported as entity attribute
      key.startsWith("ui.card.weather.attributes")
    ) {
      const entity = this.hass.states[this._config.entity];

      if (entity) {
        result = this.hass.formatEntityAttributeName(
          entity,
          key.replace("ui.card.weather.attributes.", "")
        );
      }
    }

    if (!result) {
      result = this.hass.localize(key);
    }

    return result;
  };
}

const moveDottedKeysToNested = (obj: Record<string, any>) => {
  const result: Record<string, any> = { ...obj };

  for (const key of Object.keys(obj)) {
    if (
      !key.startsWith("forecast.") &&
      !key.startsWith("forecast_action.") &&
      !key.startsWith("current.") &&
      !key.startsWith("monthly_grid.")
    )
      continue;

    const parts = key.split(".");
    if (parts.length < 2) continue;

    const [prefix, prop] = parts;
    if (!prefix || !prop) continue;

    if (!result[prefix] || typeof result[prefix] !== "object") {
      result[prefix] = {};
    }

    result[prefix][prop] = obj[key];
    delete result[key];
  }

  return result;
};

const denormalizeConfig = (obj: Record<string, any>) => {
  const result = flattenNestedKeys(obj);

  if (result.show_hourly_forecast === undefined) result.show_hourly_forecast = true;
  if (result.show_daily_forecast === undefined) result.show_daily_forecast = true;
  if (result["forecast.daily_columns"] === undefined) result["forecast.daily_columns"] = 6;
  if (result["forecast.daily_slots"] === undefined) result["forecast.daily_slots"] = 30;

  // Migrate legacy root-level temperature_entity to current.temperature_entity
  // Prefer current.temperature_entity if both are defined
  if (result.temperature_entity && !result["current.temperature_entity"]) {
    result["current.temperature_entity"] = result.temperature_entity;
  }
  delete result.temperature_entity;

  if (result.show_condition_effects === true) {
    result.show_condition_effects = [...WEATHER_EFFECTS];
  }

  if (result["current.show_attributes"] === true) {
    result["current.show_attributes"] = [...CURRENT_WEATHER_ATTRIBUTES];
  }

  // Handle show_attributes that may contain objects with entity references
  const showAttrs = result["current.show_attributes"];
  if (Array.isArray(showAttrs)) {
    // Extract attribute entities and normalize the array
    const normalizedAttrs: string[] = [];

    for (const item of showAttrs) {
      if (typeof item === "string") {
        normalizedAttrs.push(item);
      } else if (typeof item === "object" && item.name) {
        normalizedAttrs.push(item.name);
        // Store entity in flattened format for the form
        if (item.entity) {
          result[`current.attribute_entity_${item.name}`] = item.entity;
        }
      }
    }

    result["current.show_attributes"] = normalizedAttrs;
  }

  return result;
};

const flattenNestedKeys = (obj: Record<string, any>) => {
  const result: Record<string, any> = {};

  for (const key in obj) {
    const value = obj[key];

    if (
      key === "forecast" &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const innerKey in value) {
        result[`forecast.${innerKey}`] = value[innerKey];
      }
      continue;
    }

    if (
      key === "current" &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const innerKey in value) {
        result[`current.${innerKey}`] = value[innerKey];
      }
      continue;
    }

    if (
      key === "forecast_action" &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const innerKey in value) {
        result[`forecast_action.${innerKey}`] = value[innerKey];
      }
      continue;
    }

    if (
      key === "monthly_grid" &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      for (const innerKey in value) {
        result[`monthly_grid.${innerKey}`] = value[innerKey];
      }
      continue;
    }

    result[key] = value;
  }

  return result;
};

declare global {
  interface HTMLElementTagNameMap {
    "meteo-ua-weather-forecast-card-editor": WeatherForecastCardEditor;
  }
}
