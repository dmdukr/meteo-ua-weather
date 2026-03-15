"""Install/uninstall integration and card files to HA config directory."""
import logging
import os
import shutil
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

BUNDLE_DIR = Path("/app/bundle")
CONFIG_DIR = Path("/config")

INTEGRATION_SRC = BUNDLE_DIR / "custom_components" / "meteo_ua"
INTEGRATION_DST = CONFIG_DIR / "custom_components" / "meteo_ua"

CARD_SRC = BUNDLE_DIR / "www" / "meteo-ua-weather-forecast-card.js"
CARD_DST = CONFIG_DIR / "www" / "meteo-ua-weather-forecast-card.js"


def is_integration_installed() -> bool:
    return INTEGRATION_DST.exists() and (INTEGRATION_DST / "manifest.json").exists()


def is_card_installed() -> bool:
    return CARD_DST.exists()


def install_integration() -> bool:
    """Copy integration files to custom_components. Returns True if installed."""
    if is_integration_installed():
        # Check version — update if bundle is newer
        try:
            import json
            installed = json.loads((INTEGRATION_DST / "manifest.json").read_text())
            bundled = json.loads((INTEGRATION_SRC / "manifest.json").read_text())
            if installed.get("version") == bundled.get("version"):
                _LOGGER.info("Integration already installed (v%s)", installed.get("version"))
                return False
            _LOGGER.info("Updating integration %s → %s", installed.get("version"), bundled.get("version"))
        except Exception:
            pass

    _LOGGER.info("Installing integration to %s", INTEGRATION_DST)
    INTEGRATION_DST.parent.mkdir(parents=True, exist_ok=True)
    if INTEGRATION_DST.exists():
        shutil.rmtree(INTEGRATION_DST)
    shutil.copytree(INTEGRATION_SRC, INTEGRATION_DST)
    return True


def install_card() -> bool:
    """Copy card JS to www/. Returns True if installed."""
    if is_card_installed():
        # Check size — update if different
        if CARD_DST.stat().st_size == CARD_SRC.stat().st_size:
            _LOGGER.info("Card already installed")
            return False

    _LOGGER.info("Installing card to %s", CARD_DST)
    CARD_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CARD_SRC, CARD_DST)
    return True


def uninstall_integration() -> None:
    """Remove integration files."""
    if INTEGRATION_DST.exists():
        _LOGGER.info("Removing integration from %s", INTEGRATION_DST)
        shutil.rmtree(INTEGRATION_DST)


def uninstall_card() -> None:
    """Remove card JS."""
    if CARD_DST.exists():
        _LOGGER.info("Removing card from %s", CARD_DST)
        CARD_DST.unlink()


def install_all() -> bool:
    """Install integration + card. Returns True if anything was installed/updated."""
    changed = False
    if INTEGRATION_SRC.exists():
        changed |= install_integration()
    else:
        _LOGGER.warning("Integration bundle not found at %s", INTEGRATION_SRC)

    if CARD_SRC.exists():
        changed |= install_card()
    else:
        _LOGGER.warning("Card bundle not found at %s", CARD_SRC)

    return changed


def uninstall_all() -> None:
    """Remove integration + card."""
    uninstall_integration()
    uninstall_card()
