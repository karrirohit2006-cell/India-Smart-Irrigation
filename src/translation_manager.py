"""
Translation Resource Manager for Smart Irrigation Planner.
Loads, manages, and serves translation resources from organized JSON files in data/translations/.
Provides fast cached lookups, fallback resolution, and API serializations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.languages_registry import LANGUAGES_REGISTRY, get_language

logger = logging.getLogger("translation_manager")

TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "translations"
_TRANSLATIONS_CACHE: Dict[str, Dict[str, str]] = {}


def load_all_translations() -> Dict[str, Dict[str, str]]:
    """Load all JSON translation files from data/translations/ into in-memory cache."""
    global _TRANSLATIONS_CACHE
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    loaded = {}

    for code, lang in LANGUAGES_REGISTRY.items():
        fpath = TRANSLATIONS_DIR / f"{code}.json"
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        loaded[code] = data
            except Exception as e:
                logger.error(f"Failed to load translation file {fpath}: {e}")

    # Fallback to English if English exists
    en_dict = loaded.get("en", {})
    for code, lang in LANGUAGES_REGISTRY.items():
        if code not in loaded:
            loaded[code] = dict(en_dict)
        else:
            # Fill any missing keys with English
            for k, v in en_dict.items():
                if k not in loaded[code]:
                    loaded[code][k] = v

    _TRANSLATIONS_CACHE = loaded
    logger.info(f"Loaded translations for {len(_TRANSLATIONS_CACHE)} languages.")
    return _TRANSLATIONS_CACHE


def get_translations(lang_code: str) -> Dict[str, str]:
    """Get all key-value translations for a specific language code."""
    if not _TRANSLATIONS_CACHE:
        load_all_translations()
    code = (lang_code or "en").lower().strip()
    return _TRANSLATIONS_CACHE.get(code) or _TRANSLATIONS_CACHE.get("en", {})


def get_text(lang_code: str, key: str, default: Optional[str] = None) -> str:
    """Get a specific translated text string with English fallback."""
    dict_trans = get_translations(lang_code)
    if key in dict_trans:
        return dict_trans[key]
    en_trans = get_translations("en")
    return en_trans.get(key, default or key)


def get_all_translations() -> Dict[str, Dict[str, str]]:
    """Return all cached translations across all supported languages."""
    if not _TRANSLATIONS_CACHE:
        load_all_translations()
    return _TRANSLATIONS_CACHE


def reload_translations() -> Dict[str, Dict[str, str]]:
    """Force reload of all translation files from disk."""
    return load_all_translations()


# Pre-load on module import
load_all_translations()
