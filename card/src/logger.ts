const TAG = "[weather-forecast-card]";

export const logger = {
  debug: (...args: unknown[]) => console.debug(TAG, ...args),
  info: (...args: unknown[]) => console.info(TAG, ...args),
  warn: (...args: unknown[]) => console.warn(TAG, ...args),
  error: (...args: unknown[]) => console.error(TAG, ...args),
};
