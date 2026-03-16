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


def _file_hash(path: Path) -> str:
    """MD5 hash of a single file."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def _dir_hash(path: Path, exclude_dirs: set[str] | None = None) -> str:
    """Calculate a quick hash of all files in a directory."""
    exclude = exclude_dirs or set()
    h = hashlib.md5()
    if not path.exists():
        return ""
    for f in sorted(path.rglob("*")):
        if f.is_file() and not any(ex in f.parts for ex in exclude):
            h.update(f.read_bytes())
    return h.hexdigest()


def is_integration_installed() -> bool:
    return INTEGRATION_DST.exists() and (INTEGRATION_DST / "manifest.json").exists()


def _detect_changes() -> dict[str, bool]:
    """Compare bundle vs installed, return what changed.

    Returns dict with keys:
        'integration' — Python files changed (need HA restart)
        'card' — JS frontend changed (need browser refresh)
        'new_install' — not installed at all
    """
    if not is_integration_installed():
        return {"new_install": True, "integration": True, "card": True}

    result = {"new_install": False, "integration": False, "card": False}

    # Check card JS separately
    src_card = INTEGRATION_SRC / "frontend" / "meteo-ua-weather-forecast-card.js"
    dst_card = INTEGRATION_DST / "frontend" / "meteo-ua-weather-forecast-card.js"
    if _file_hash(src_card) != _file_hash(dst_card):
        result["card"] = True

    # Check integration Python files (everything except frontend/)
    src_hash = _dir_hash(INTEGRATION_SRC, exclude_dirs={"frontend", "__pycache__"})
    dst_hash = _dir_hash(INTEGRATION_DST, exclude_dirs={"frontend", "__pycache__"})
    if src_hash != dst_hash:
        result["integration"] = True

    return result


def install_integration() -> dict[str, bool]:
    """Copy integration files. Returns dict of what changed."""
    changes = _detect_changes()

    if not changes["integration"] and not changes["card"]:
        try:
            v = json.loads((INTEGRATION_DST / "manifest.json").read_text()).get("version", "?")
            _LOGGER.info("Integration up to date (v%s) — no changes", v)
        except Exception:
            _LOGGER.info("Integration up to date — no changes")
        return changes

    # Log what changed
    parts = []
    if changes["new_install"]:
        parts.append("new install")
    else:
        if changes["integration"]:
            parts.append("integration code")
        if changes["card"]:
            parts.append("frontend card")
    _LOGGER.info("Changes detected: %s", ", ".join(parts))

    try:
        src_v = json.loads((INTEGRATION_SRC / "manifest.json").read_text()).get("version", "?")
        if changes["new_install"]:
            _LOGGER.info("Installing integration v%s to %s", src_v, INTEGRATION_DST)
        else:
            dst_v = json.loads((INTEGRATION_DST / "manifest.json").read_text()).get("version", "?")
            if src_v != dst_v:
                _LOGGER.info("Updating integration v%s → v%s", dst_v, src_v)
            else:
                _LOGGER.info("Updating integration v%s (files changed)", src_v)
    except Exception:
        pass

    # Always copy full bundle (atomic update)
    INTEGRATION_DST.parent.mkdir(parents=True, exist_ok=True)
    if INTEGRATION_DST.exists():
        shutil.rmtree(INTEGRATION_DST)
    shutil.copytree(INTEGRATION_SRC, INTEGRATION_DST)

    return changes


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


def install_all() -> dict[str, bool]:
    """Install integration. Returns dict of what changed."""
    _cleanup_legacy_card()

    if INTEGRATION_SRC.exists():
        return install_integration()

    _LOGGER.warning("Integration bundle not found at %s", INTEGRATION_SRC)
    return {"new_install": False, "integration": False, "card": False}


def uninstall_all() -> None:
    """Remove integration + legacy card."""
    uninstall_integration()
    _cleanup_legacy_card()
