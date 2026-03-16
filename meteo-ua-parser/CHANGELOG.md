# Changelog

## 0.23.0

**Addon** v0.23.0 | **Integration** v1.6.0 | **Card** v1.1.0

- Colored logs in Supervisor UI (green INFO, yellow WARNING, red ERROR)
- Fixed card version detection in startup log
- Removed auto-restart — only notifications

## 0.22.0

**Addon** v0.22.0 | **Integration** v1.6.0 | **Card** v1.1.0

- Fixed card version showing as "?" in startup log

## 0.21.0

**Addon** v0.21.0 | **Integration** v1.6.0 | **Card** v1.1.0

- Show all 3 version numbers in startup log
- Smart notifications: integration change → restart HA, card change → refresh browser
- No auto-restart — user decides when to restart
- Hash-based file comparison for reliable update detection
- Colored log output (errors red, warnings yellow)
- No more manual city configuration — integration registers cities automatically

## 0.18.0

**Addon** v0.18.0 | **Integration** v1.6.0 | **Card** v1.1.0

- Hash-based install detection
- Auto HA restart after installation
- Renamed to "Meteo UA Weather"

## 0.9.0

**Addon** v0.9.0 | **Integration** v1.5.0 | **Card** v1.0.0

- Auto-install integration and card on first start
- Persistent notification for HA restart
- Headless Chromium parser for meteo.ua
