"""Install/uninstall integration files to HA config directory.

Card JS is bundled inside the integration (frontend/) and registered
via Lovelace resources in __init__.py — no separate www/ copy needed.
"""
import hashlib
import json
import logging
import shutil
from pathlib import Path

_LOGGER = logging.getLogger("installer")

BUNDLE_DIR = Path("/app/bundle")
CONFIG_DIR = Path("/config")

INTEGRATION_SRC = BUNDLE_DIR / "custom_components" / "meteo_ua"
INTEGRATION_DST = CONFIG_DIR / "custom_components" / "meteo_ua"

# Legacy card location — clean up if exists
LEGACY_CARD = CONFIG_DIR / "www" / "meteo-ua-weather-forecast-card.js"


def _dir_hash(path: Path) -> str:
    """Calculate a quick hash of all files in a directory."""
    h = hashlib.md5()
    if not path.exists():
        return ""
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in str(f):
            h.update(f.read_bytes())
    return h.hexdigest()


def is_integration_installed() -> bool:
    return INTEGRATION_DST.exists() and (INTEGRATION_DST / "manifest.json").exists()


def install_integration() -> bool:
    """Copy integration files to custom_components. Returns True if installed/updated."""
    if is_integration_installed():
        # Compare content hashes — catches any file change, not just version bump
        src_hash = _dir_hash(INTEGRATION_SRC)
        dst_hash = _dir_hash(INTEGRATION_DST)
        if src_hash == dst_hash:
            try:
                v = json.loads((INTEGRATION_DST / "manifest.json").read_text()).get("version", "?")
                _LOGGER.info("Integration already installed and up to date (v%s)", v)
            except Exception:
                _LOGGER.info("Integration already installed and up to date")
            return False
        # Files differ — update
        try:
            src_v = json.loads((INTEGRATION_SRC / "manifest.json").read_text()).get("version", "?")
            dst_v = json.loads((INTEGRATION_DST / "manifest.json").read_text()).get("version", "?")
            _LOGGER.info("Updating integration v%s → v%s", dst_v, src_v)
        except Exception:
            _LOGGER.info("Updating integration (files changed)")

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
