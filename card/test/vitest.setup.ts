import { beforeAll } from "vitest";
import { WeatherForecastCard } from "../src/weather-forecast-card";

beforeAll(() => {
  console.log = () => {};
  console.info = () => {};
  console.warn = () => {};
  console.error = () => {};

  // Register under both names for backward-compatible test fixtures
  if (!customElements.get("weather-forecast-card")) {
    customElements.define("weather-forecast-card", class extends WeatherForecastCard {} );
  }
});
