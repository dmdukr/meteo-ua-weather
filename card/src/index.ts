import { WeatherForecastCard } from "./weather-forecast-card";
import * as pjson from "../package.json";
import "./editor/weather-forecast-card-editor";

declare global {
  interface Window {
    customCards: Array<object>;
  }
}

customElements.define("meteo-ua-weather-forecast-card", WeatherForecastCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "meteo-ua-weather-forecast-card",
  name: "Meteo UA Weather Forecast",
  description: "Weather forecast card for Meteo UA Weather",
});

console.info(
  `%cMETEO-UA-METEO-UA-WEATHER-FORECAST-CARD %c${pjson.version}`,
  "color: orange; font-weight: bold; background: black",
  "color: white; font-weight: bold; background: dimgray"
);
