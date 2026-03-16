"""Install/uninstall integration files to HA config directory.

Card JS is bundled inside the integration (frontend/) and registered
via add_extra_js_url in __init__.py — no separate www/ copy needed.
"""
import logging
import shutil
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

BUNDLE_DIR = Path("/app/bundle")
CONFIG_DIR = Path("/config")

INTEGRATION_SRC = BUNDLE_DIR / "custom_components" / "meteo_ua"
INTEGRATION_DST = CONFIG_DIR / "custom_components" / "meteo_ua"

# Legacy card location — clean up if exists
LEGACY_CARD = CONFIG_DIR / "www" / "meteo-ua-weather-forecast-card.js"


def is_integration_installed() -> bool:
    return INTEGRATION_DST.exists() and (INTEGRATION_DST / "manifest.json").exists()


def install_integration() -> bool:
    """Copy integration files to custom_components. Returns True if installed."""
    if is_integration_installed():
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


def uninstall_integration() -> None:
    """Remove integration files."""
    if INTEGRATION_DST.exists():
        _LOGGER.info("Removing integration from %s", INTEGRATION_DST)
        shutil.rmtree(INTEGRATION_DST)


def _cleanup_legacy_card() -> None:
    """Remove old card copy from www/ if it exists."""
    if LEGACY_CARD.exists():
        try:
            LEGACY_CARD.unlink()
            _LOGGER.info("Removed legacy card from %s", LEGACY_CARD)
        except OSError as exc:
            _LOGGER.warning("Failed to remove legacy card: %s", exc)


def install_all() -> bool:
    """Install integration. Returns True if anything was installed/updated."""
    _cleanup_legacy_card()

    if INTEGRATION_SRC.exists():
        return install_integration()

    _LOGGER.warning("Integration bundle not found at %s", INTEGRATION_SRC)
    return False


def uninstall_all() -> None:
    """Remove integration + legacy card."""
    uninstall_integration()
    _cleanup_legacy_card()
