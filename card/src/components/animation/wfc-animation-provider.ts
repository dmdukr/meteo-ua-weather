import { LitElement, PropertyValues, html, nothing, TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  ExtendedHomeAssistant,
  WeatherEffect,
  WeatherForecastCardConfig,
} from "../../types";
import { styles } from "./wfc-animation.styles";
import { styleMap } from "lit/directives/style-map.js";
import { getSuntimesInfo, random } from "../../helpers";
import {
  ForecastAttribute,
  getMaxPrecipitationForUnit,
  getNormalizedWindSpeed,
  getWeatherUnit,
  WeatherEntity,
} from "../../data/weather";

const PRECIPITATION_INTENSITY_MAX = 10;
const PRECIPITATION_INTENSITY_MEDIUM = 3;
const WIND_SPEED_MS_MAX = 14;
const SNOW_MAX_PARTICLES = 75;
const RAIN_MAX_PARTICLES = 150;
const HAIL_MAX_PARTICLES = 60;

const FOG_ORB_COUNT = 135;
const CLOUD_COUNT = 16;
const PARTLY_CLOUD_COUNT = 8;
const WIND_STREAK_COUNT = 8;
const LEAF_COUNT = 40;
const STAR_COUNT = 30;
const SUN_RAY_COUNT = 30;

// --- Shared SVG Templates ---

const SNOWFLAKE_SVG = html`
  <svg class="snowflake" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke="white" stroke-width="3" stroke-linecap="round">
      <line x1="50" y1="5" x2="50" y2="95"/>
      <line x1="50" y1="5" x2="35" y2="20"/><line x1="50" y1="5" x2="65" y2="20"/>
      <line x1="50" y1="95" x2="35" y2="80"/><line x1="50" y1="95" x2="65" y2="80"/>
      <line x1="11" y1="27.5" x2="89" y2="72.5"/>
      <line x1="11" y1="27.5" x2="11" y2="45"/><line x1="11" y1="27.5" x2="27" y2="25"/>
      <line x1="89" y1="72.5" x2="89" y2="55"/><line x1="89" y1="72.5" x2="73" y2="75"/>
      <line x1="89" y1="27.5" x2="11" y2="72.5"/>
      <line x1="89" y1="27.5" x2="89" y2="45"/><line x1="89" y1="27.5" x2="73" y2="25"/>
      <line x1="11" y1="72.5" x2="11" y2="55"/><line x1="11" y1="72.5" x2="27" y2="75"/>
      <line x1="50" y1="30" x2="38" y2="37"/><line x1="50" y1="30" x2="62" y2="37"/>
      <line x1="50" y1="70" x2="38" y2="63"/><line x1="50" y1="70" x2="62" y2="63"/>
    </g>
  </svg>
`;

const LEAF_PATHS: TemplateResult[] = [
  html`<path d="M20 2C12 8 4 18 8 28c2 5 7 8 12 10 5-2 10-5 12-10 4-10-4-20-12-26z" fill="url(#leaf-fill)" filter="url(#leaf-blur)"/>
       <path d="M20 8v24M14 14c3 2 6 2 9 0M13 22c3 2 7 2 10 0" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>`,
  html`<path d="M5 20C10 10 18 4 28 6c5 1 9 5 10 10-1 5-5 9-10 10-10 2-20-2-23-6z" fill="url(#leaf-fill)" filter="url(#leaf-blur)"/>
       <path d="M8 20h26M18 12c1 4 1 8 0 12" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>`,
  html`<path d="M20 4C14 6 6 14 8 24c1 4 5 8 10 10 3-1 6-3 8-6 4-6 3-14-1-20-1-2-3-3-5-4z" fill="url(#leaf-fill)" filter="url(#leaf-blur)"/>
       <path d="M20 8v24M15 16c2 2 5 3 8 1" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>`,
];

// --- Particle Types ---

type BaseParticle = { x: string; delay: string; duration?: string };
type Snowflake = BaseParticle & { type: "snow"; size: string; opacity: string; blur: string; shadowSpread: string; driftAmplitude: string; driftFrequency: string };
type PrecipParticle = BaseParticle & { type: "rain" | "hail"; landingPosY: string; size?: string };
type Star = BaseParticle & { type: "star"; y: string; size: string; opacity: string };
type SunRay = { type: "sunray"; angle: string; height: string; width: string };
type WeatherParticle = Snowflake | PrecipParticle | Star | SunRay;

// --- Effect Renderer Map ---

const EFFECT_RENDERERS: Record<string, string> = {
  sky: "renderSky", moon: "renderMoon", sun: "renderSun",
  rain: "renderRain", snow: "renderSnow", lightning: "renderLightning",
  clouds: "renderClouds", partlyclouds: "renderPartlyClouds",
  fog: "renderFog", hail: "renderHail", wind: "renderWind",
  warning: "renderWarning",
};

const PARTICLE_COMPUTERS: Record<string, string> = {
  rain: "computePrecipParticles", snow: "computeSnowParticles",
  moon: "computeStarParticles", sun: "computeSunRayParticles",
  hail: "computePrecipParticles",
};

// --- Helper to generate numbered divs ---

const numberedDivs = (baseClass: string, prefix: string, count: number, extra = "") =>
  Array.from({ length: count }, (_, i) =>
    html`<div class="${baseClass} ${prefix}-${i + 1}${extra ? ` ${extra}` : ""}"></div>`
  );

@customElement("wfc-animation-provider")
export class WeatherAnimationProvider extends LitElement {
  @property({ attribute: false }) hass!: ExtendedHomeAssistant;
  @property({ attribute: false }) weatherEntity!: WeatherEntity;
  @property({ attribute: false }) currentForecast?: ForecastAttribute;
  @property({ attribute: false }) config!: WeatherForecastCardConfig;

  @state() _isDark: boolean = false;
  @state() _containerHeight: number = 0;

  private _particles: WeatherParticle[] = [];
  private _resizeObserver?: ResizeObserver;

  static styles = styles;

  public connectedCallback(): void {
    super.connectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = new ResizeObserver((entries) => {
      const height = Math.round(entries[0]?.contentRect.height || 0);
      if (this._containerHeight !== height) {
        this._containerHeight = height;
        this._particles = this.computeParticles();
      }
    });
    this._resizeObserver.observe(this);
  }

  public disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
  }

  protected willUpdate(changedProps: PropertyValues) {
    if (changedProps.has("hass")) {
      const oldHass = changedProps.get("hass") as ExtendedHomeAssistant | undefined;
      const currentDark = this.hass?.themes?.darkMode;
      if (oldHass?.themes?.darkMode !== currentDark) {
        this._isDark = currentDark ?? false;
      }
    }
    if (changedProps.has("config") || changedProps.has("weatherEntity") || changedProps.has("currentForecast")) {
      this._particles = this.computeParticles();
    }
  }

  protected updated(changedProps: PropertyValues) {
    if (changedProps.has("hass")) {
      this.classList.toggle("dark", this._isDark);
      this.classList.toggle("light", !this._isDark);
    }
  }

  protected render() {
    const active = this.getActiveEffects();
    if (!active.length) return nothing;
    return html`${active.map((effect) => {
      const method = EFFECT_RENDERERS[effect];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return method ? (this as any)[method]() : nothing;
    })}`;
  }

  // --- Particle Computation ---

  private computeParticles(): WeatherParticle[] {
    const particles: WeatherParticle[] = [];
    for (const effect of this.getActiveEffects()) {
      const method = PARTICLE_COMPUTERS[effect];
      if (method) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        particles.push(...(this as any)[method](effect));
      }
    }
    return particles;
  }

  private computeSnowParticles(): Snowflake[] {
    const intensity = this.computeIntensity();
    const safeCount = Math.max(5, Math.round((intensity / PRECIPITATION_INTENSITY_MAX) * SNOW_MAX_PARTICLES));
    const columnWidth = 115 / safeCount;

    return Array.from({ length: safeCount }, (_, i) => {
      const currentX = -15 + i * columnWidth + random(0, columnWidth * 0.5);
      const depth = Math.random();
      const flakeSize = depth * 25 + 10;

      return {
        type: "snow" as const,
        x: `${currentX.toFixed(1)}%`,
        delay: random(0, 5, true).toFixed(1),
        duration: (4.5 / (depth + 0.5) + random(0, 0.8)).toFixed(1),
        size: flakeSize.toFixed(0),
        opacity: (depth * 0.3 + 0.7).toFixed(1),
        blur: "0.0",
        shadowSpread: (flakeSize * 0.9).toFixed(1),
        driftAmplitude: (10 + depth * 25).toFixed(0),
        driftFrequency: (2 + Math.random() * 2).toFixed(2),
      };
    });
  }

  private computePrecipParticles(effect: "rain" | "hail"): PrecipParticle[] {
    const intensity = this.computeIntensity();
    const isHail = effect === "hail";
    const maxParticles = isHail ? HAIL_MAX_PARTICLES : RAIN_MAX_PARTICLES;
    const minCount = isHail ? 8 : 10;
    const safeCount = Math.max(minCount, Math.round((intensity / PRECIPITATION_INTENSITY_MAX) * maxParticles));
    const columnWidth = 100 / safeCount;

    return Array.from({ length: safeCount }, (_, i) => {
      const currentX = isHail
        ? i * columnWidth + random(0, columnWidth * 0.8)
        : (i + 0.5) * columnWidth + random(-columnWidth * 0.4, columnWidth * 0.4);
      const depthVariance = random(0.85, 1, true);

      return {
        type: effect,
        x: `${currentX.toFixed(1)}%`,
        delay: random(isHail ? 0.1 : 0, isHail ? 0.4 : 1, true).toFixed(2),
        duration: random(isHail ? 0.3 : 0.4, isHail ? 0.5 : 0.8, true).toFixed(2),
        landingPosY: (this._containerHeight * depthVariance).toFixed(0),
        ...(isHail ? { size: random(2, 5).toFixed(0) } : {}),
      };
    });
  }

  private computeStarParticles(): Star[] {
    const columns = 6;
    const rows = 5;
    const cellWidth = 100 / columns;
    const cellHeight = 30 / rows;

    return Array.from({ length: STAR_COUNT }, (_, i) => {
      const col = i % columns;
      const row = Math.floor(i / columns);
      return {
        type: "star" as const,
        x: `${random(col * cellWidth + cellWidth * 0.15, (col + 1) * cellWidth - cellWidth * 0.15).toFixed(0)}`,
        y: `${random(row * cellHeight + cellHeight * 0.15, (row + 1) * cellHeight - cellHeight * 0.15).toFixed(0)}`,
        size: `${random(1, 3)}`,
        opacity: random(0.3, 1, true).toFixed(2),
        delay: random(0, 5, true).toFixed(1),
      };
    });
  }

  private computeSunRayParticles(): SunRay[] {
    return Array.from({ length: SUN_RAY_COUNT }, () => ({
      type: "sunray" as const,
      angle: `${random(0, 360)}`,
      height: `${random(100, 200)}`,
      width: `${random(5, 15)}`,
    }));
  }

  // --- Active Effects Resolution ---

  private getActiveEffects(): WeatherEffect[] {
    const state = this.weatherEntity?.state;
    const effectConfig = this.config.show_condition_effects;
    if (!effectConfig || !state) return [];

    const effects = new Set<WeatherEffect>();
    const isEnabled = (e: WeatherEffect) =>
      effectConfig === true || (Array.isArray(effectConfig) && effectConfig.includes(e));
    const addIf = (e: WeatherEffect) => { if (isEnabled(e)) effects.add(e); };

    const night = this._isNight();

    // Precipitation — overcast conditions get night-sky when dark
    if (state === "snowy") { addIf("clouds"); addIf("snow"); }
    else if (state === "snowy-rainy") { addIf("clouds"); addIf("snow"); addIf("rain"); }
    else if (state.includes("rainy") || state === "pouring") { addIf("rain"); addIf("clouds"); }
    if (state.includes("lightning")) { addIf("clouds"); addIf("lightning"); }

    // Clear / partly cloudy
    if (state === "sunny" || state === "clear-night") {
      addIf("sky");
      if (night) addIf("moon"); else addIf("sun");
    }
    if (state === "cloudy") addIf("clouds");
    if (state === "partlycloudy") {
      addIf("partlyclouds");
      if (night) { addIf("sky"); addIf("moon"); }
      else { addIf("sky"); addIf("sun"); }
    }

    // Atmosphere
    if (state === "fog") { addIf("fog"); if (night) addIf("sky"); }
    if (state === "hail") { addIf("hail"); addIf("clouds"); }
    if (state === "windy") {
      addIf("sky"); addIf("wind");
      if (night) addIf("moon"); else addIf("sun");
    }
    if (state === "windy-variant") {
      addIf("sky"); addIf("partlyclouds"); addIf("wind");
      if (night) addIf("moon"); else addIf("sun");
    }
    if (state === "exceptional") addIf("warning");

    return Array.from(effects);
  }

  // --- Night detection (shared) ---

  private _isNight(): boolean {
    const state = this.weatherEntity?.state;
    if (state === "sunny") return false;
    if (state === "clear-night") return true;
    return getSuntimesInfo(this.hass, new Date())?.isNightTime ?? false;
  }

  // --- Renderers ---

  private renderSky() {
    return html`<div class="${this._isNight() ? "night-sky" : "sky"}"></div>`;
  }

  private renderSun() {
    const rays = this._particles.filter((p): p is SunRay => p.type === "sunray");
    return html`
      <div class="sun"><div class="ray-box">
        ${rays.map((ray) => html`<div class="sun-ray" style="${styleMap({
          transform: `translate(-50%, 0) rotate(${ray.angle}deg)`,
          height: `${ray.height}px`, width: `${ray.width}px`,
        })}"></div>`)}
      </div></div>`;
  }

  private renderSnow() {
    this.style.setProperty("--container-height", `${this._containerHeight}px`);
    this.style.setProperty("--fall-angle", `${this.computeFallingAngle()}deg`);
    return (this._particles.filter((p) => p.type === "snow") as Snowflake[]).map(
      (p) => html`
        <div class="snowflake-path" style="${styleMap({
          "--duration": `${p.duration}s`, "--delay": `${p.delay}s`, "--pos-x": p.x,
          "--flake-size": `${p.size}px`, "--flake-opacity": p.opacity,
          "--flake-blur": `${p.blur}px`, "--flake-shadow-spread": `${p.shadowSpread}px`,
          "--drift-amplitude": `${p.driftAmplitude}px`, "--drift-frequency": p.driftFrequency,
        })}">${SNOWFLAKE_SVG}</div>`
    );
  }

  private renderRain() {
    const isPouring = this.weatherEntity?.state === "pouring";
    this.style.setProperty("--container-height", `${this._containerHeight}px`);
    this.style.setProperty("--drop-width", isPouring ? "2px" : "1px");
    this.style.setProperty("--fall-angle", `${this.computeFallingAngle(true)}deg`);
    return (this._particles.filter((p) => p.type === "rain") as PrecipParticle[]).map(
      (p) => html`
        <div class="raindrop-path" style="${styleMap({
          "--duration": `${p.duration}s`, "--delay": `${p.delay}s`,
          "--pos-x": p.x, "--landing-pos-y": `${p.landingPosY}px`,
        })}"><div class="raindrop"></div><div class="splat"></div></div>`
    );
  }

  private renderHail() {
    this.style.setProperty("--container-height", `${this._containerHeight}px`);
    this.style.setProperty("--fall-angle", `${this.computeFallingAngle(true)}deg`);
    return (this._particles.filter((p) => p.type === "hail") as PrecipParticle[]).map(
      (p) => html`
        <div class="hailstone-path" style="${styleMap({
          "--duration": `${p.duration}s`, "--delay": `${p.delay}s`,
          "--pos-x": p.x, "--hail-size": `${p.size}px`, "--landing-pos-y": `${p.landingPosY}px`,
        })}"><div class="hailstone"></div></div>`
    );
  }

  private renderLightning() {
    return html`<div class="lightning-flash"></div>`;
  }

  private renderMoon() {
    return html`
      <div class="moon"></div>
      ${(this._particles.filter((p) => p.type === "star") as Star[]).map(
        (p) => html`<div class="star" style="${styleMap({
          left: `${p.x}%`, top: `${p.y}%`, width: `${p.size}px`,
          height: `${p.size}px`, opacity: p.opacity, animationDelay: `${p.delay}s`,
        })}"></div>`
      )}`;
  }

  private renderClouds() {
    return html`<div class="${this._isNight() ? "overcast-sky-night" : "overcast-sky"}"></div>${numberedDivs("cloud", "cloud-pc", CLOUD_COUNT)}`;
  }

  private renderPartlyClouds() {
    return numberedDivs("cloud", "cloud-pc", PARTLY_CLOUD_COUNT, "cloud-white");
  }

  private renderFog() {
    return html`<div class="${this._isNight() ? "fog-sky-night" : "fog-sky"}"></div>${numberedDivs("fog-orb", "fog-orb", FOG_ORB_COUNT)}`;
  }

  private renderWind() {
    const leaves = Array.from({ length: LEAF_COUNT }, () => ({
      y: `${random(2, 45)}%`,
      size: random(18, 30),
      duration: random(3, 6, true).toFixed(1),
      delay: random(0, 5, true).toFixed(1),
      spinDuration: random(1.5, 3, true).toFixed(1),
      opacity: random(0.4, 0.8, true).toFixed(2),
      variant: random(0, 2),
    }));

    return html`
      ${numberedDivs("wind-streak", "wind-streak", WIND_STREAK_COUNT)}
      ${leaves.map((l) => html`
        <div class="wind-leaf" style="${styleMap({
          top: l.y, "--leaf-duration": `${l.duration}s`, "--leaf-delay": `${l.delay}s`,
          "--leaf-spin": `${l.spinDuration}s`, "--leaf-size": `${l.size}px`, opacity: l.opacity,
        })}">
          <svg class="wind-leaf-svg" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <filter id="leaf-blur"><feGaussianBlur in="SourceGraphic" stdDeviation="0.8"/></filter>
              <radialGradient id="leaf-fill">
                <stop offset="0%" stop-color="white" stop-opacity="1"/>
                <stop offset="60%" stop-color="white" stop-opacity="0.95"/>
                <stop offset="100%" stop-color="white" stop-opacity="0.3"/>
              </radialGradient>
            </defs>
            ${LEAF_PATHS[l.variant]}
          </svg>
        </div>`
      )}`;
  }

  private renderWarning() {
    return html`<div class="warning-overlay"></div>`;
  }

  // --- Physics ---

  private computeIntensity(): number {
    const precip = this.currentForecast?.precipitation || 0;
    if (precip > 0) {
      const unit = getWeatherUnit(this.hass, this.weatherEntity, "precipitation");
      const maxPrecip = getMaxPrecipitationForUnit(unit, "hourly");
      if (maxPrecip > 0) {
        return Math.min(PRECIPITATION_INTENSITY_MAX, Math.ceil((precip / maxPrecip) * PRECIPITATION_INTENSITY_MAX));
      }
    }
    return this.weatherEntity?.state === "pouring" ? PRECIPITATION_INTENSITY_MAX : PRECIPITATION_INTENSITY_MEDIUM;
  }

  private computeFallingAngle(isRain: boolean = false): number {
    const forecast = this.currentForecast;
    if (forecast?.wind_bearing === undefined || forecast?.wind_speed === undefined) return 0;

    const speedMS = getNormalizedWindSpeed(this.hass, this.weatherEntity, forecast) || 0;
    const MAX_TILT = isRain ? 15 : 35;
    const speedFactor = Math.min(speedMS, WIND_SPEED_MS_MAX) / WIND_SPEED_MS_MAX;
    const radians = ((forecast.wind_bearing as number) * Math.PI) / 180;
    const curve = isRain ? 0.8 : 0.5;

    return Math.sin(radians) * Math.pow(speedFactor, curve) * MAX_TILT;
  }
}
