import { HomeAssistant, TimeFormat } from "custom-card-helpers";
import { STATE_NOT_RUNNING } from "home-assistant-js-websocket";
import * as SunCalc from "suncalc";
import memoizeOne from "memoize-one";
import { SuntimesInfo } from "./types";

export interface HourParts {
  hour: string;
  suffix?: string;
}

export interface TimeParts {
  time: string;
  suffix?: string;
}

// --- Lodash replacements ---

/**
 * Random number generator matching lodash-es `random()` behavior.
 * If either bound is a float or `floating` is true, returns a float; otherwise an integer.
 */
export const random = (min: number, max: number, floating?: boolean): number => {
  if (floating || min % 1 !== 0 || max % 1 !== 0) {
    return min + Math.random() * (max - min);
  }
  return Math.floor(Math.random() * (max - min + 1)) + min;
};

export const capitalize = (str: string): string =>
  str ? str.charAt(0).toUpperCase() + str.slice(1).toLowerCase() : "";

type DeepPartial = Record<string, unknown>;

export function deepMerge<T extends DeepPartial>(...sources: Partial<T>[]): T {
  const result: DeepPartial = {};
  for (const source of sources) {
    if (!source) continue;
    for (const key of Object.keys(source)) {
      const srcVal = (source as DeepPartial)[key];
      const tgtVal = result[key];
      if (
        srcVal &&
        typeof srcVal === "object" &&
        !Array.isArray(srcVal) &&
        tgtVal &&
        typeof tgtVal === "object" &&
        !Array.isArray(tgtVal)
      ) {
        result[key] = deepMerge(
          tgtVal as DeepPartial,
          srcVal as DeepPartial
        );
      } else {
        result[key] = srcVal;
      }
    }
  }
  return result as T;
}

// --- Date formatting ---

export const createWarningText = (
  hass: HomeAssistant | undefined,
  entity: string
): string => {
  if (!hass) {
    return "Home Assistant instance is not available.";
  }

  return hass.config.state !== STATE_NOT_RUNNING
    ? `${hass.localize("ui.card.common.entity_not_found")}: ${entity}`
    : hass.localize("ui.panel.lovelace.warning.starting");
};

export const formatDay = (
  hass: HomeAssistant | undefined,
  datetime: string | Date
): string => {
  return toDate(datetime).toLocaleDateString(getLocale(hass), {
    weekday: "short",
  });
};

export const formatDayOfMonth = (
  hass: HomeAssistant | undefined,
  datetime: string | Date
): string => {
  return toDate(datetime).toLocaleDateString(getLocale(hass), {
    day: "numeric",
  });
};

interface DateFormatOptions {
  hour: "numeric";
  minute?: "2-digit";
  hour12: boolean;
}

interface FormattedParts {
  value: string;
  suffix?: string;
}

const formatDateParts = (
  hass: HomeAssistant | undefined,
  datetime: string | Date,
  includeMinutes: boolean
): FormattedParts => {
  const date = toDate(datetime);
  const locale = getLocale(hass);
  const isAmPm = useAmPm(hass);

  const options: DateFormatOptions = {
    hour: "numeric",
    hour12: isAmPm,
  };
  if (includeMinutes) {
    options.minute = "2-digit";
  }

  try {
    const formatter = new Intl.DateTimeFormat(locale, options);
    const parts = formatter.formatToParts(date);

    const hourPart = parts.find((p) => p.type === "hour");
    const minutePart = includeMinutes
      ? parts.find((p) => p.type === "minute")
      : null;
    const dayPeriodPart = parts.find((p) => p.type === "dayPeriod");

    const mainPart = includeMinutes ? hourPart && minutePart : hourPart;

    if (mainPart) {
      let value: string;
      let afterIndex: number;

      if (includeMinutes && hourPart && minutePart) {
        const hourIndex = parts.indexOf(hourPart);
        const minuteIndex = parts.indexOf(minutePart);
        const separator = parts
          .slice(hourIndex + 1, minuteIndex)
          .map((p) => p.value)
          .join("");
        value = `${hourPart.value}${separator}${minutePart.value}`;
        afterIndex = minuteIndex;
      } else {
        value = hourPart!.value;
        afterIndex = parts.indexOf(hourPart!);
      }

      if (dayPeriodPart) {
        return { value, suffix: dayPeriodPart.value };
      }

      const suffixLiteral = parts
        .slice(afterIndex + 1)
        .filter((p) => p.type === "literal")
        .map((p) => p.value)
        .join("");

      if (suffixLiteral?.trim()) {
        return { value, suffix: suffixLiteral.trim() };
      }

      return { value };
    }
  } catch {
    // Fallback below
  }

  const fullTime = date.toLocaleTimeString(locale, options);

  if (includeMinutes) {
    const timeMatch = fullTime.match(/\d+[:.]\d+/);
    const value = timeMatch ? timeMatch[0] : fullTime;
    const suffix = fullTime.replace(/\d+[:.]\d+\s*/, "").trim();
    return suffix ? { value, suffix } : { value };
  }

  const numericMatch = fullTime.match(/\d+/);
  const value = numericMatch ? numericMatch[0] : fullTime;
  const suffix = fullTime.replace(/\d+\s*/, "").trim();
  return suffix ? { value, suffix } : { value };
};

export const formatHourParts = (
  hass: HomeAssistant | undefined,
  datetime: string | Date
): HourParts => {
  const { value, suffix } = formatDateParts(hass, datetime, false);
  return suffix ? { hour: value, suffix } : { hour: value };
};

export const formatTimeParts = (
  hass: HomeAssistant | undefined,
  datetime: string | Date
): TimeParts => {
  const { value, suffix } = formatDateParts(hass, datetime, true);
  return suffix ? { time: value, suffix } : { time: value };
};

export const normalizeDate = (dateString: string) => {
  const date = new Date(dateString);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
};

export const useAmPm = memoizeOne(
  (hass: HomeAssistant | undefined): boolean => {
    const locale = hass?.locale;
    if (
      locale?.time_format === TimeFormat.language ||
      locale?.time_format === TimeFormat.system
    ) {
      const testLanguage =
        locale.time_format === TimeFormat.language
          ? locale.language
          : undefined;
      const test = new Date("January 1, 2023 22:00:00").toLocaleString(
        testLanguage
      );
      return test.includes("10");
    }

    return locale?.time_format === TimeFormat.am_pm;
  }
);

export const getLocale = (hass: HomeAssistant | undefined): string => {
  return hass?.locale?.language || navigator.language || "en";
};

export const toDate = (datetime: string | Date): Date => {
  return typeof datetime === "string" ? new Date(datetime) : datetime;
};

export const getSuntimesInfo = (
  hass: HomeAssistant | undefined,
  datetime: string | Date
): SuntimesInfo | null => {
  const { latitude, longitude } = hass?.config || {};
  if (!latitude || !longitude) {
    return null;
  }

  const date = toDate(datetime);
  const times = SunCalc.getTimes(date, latitude, longitude);

  return {
    sunrise: times.sunrise,
    sunset: times.sunset,
    isNightTime: date < times.sunrise || date > times.sunset,
  };
};

export const average = (data: number[]): number => {
  if (data.length === 0) return 0;
  return data.reduce((a, b) => a + b, 0) / data.length;
};

export const endOfHour = (input: Date | string): Date => {
  const d = typeof input === "string" ? new Date(input) : new Date(input);

  d.setMinutes(59, 59, 999);

  return d;
};
