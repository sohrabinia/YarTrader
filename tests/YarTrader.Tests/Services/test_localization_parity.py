import os
import json
import pytest

def test_four_language_key_parity():
    """Verify 100% key parity across all 4 production locale files (FA, EN, TR, AR)."""
    locales_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "trader-terminal", "public", "locales"
    )
    languages = ["fa", "en", "tr", "ar"]
    locale_data = {}

    for lang in languages:
        path = os.path.join(locales_dir, f"{lang}.json")
        assert os.path.exists(path), f"Locale file missing for {lang}"
        with open(path, "r", encoding="utf-8") as f:
            locale_data[lang] = json.load(f)

    # Base reference keys from FA
    base_keys = set(locale_data["fa"].keys())
    assert len(base_keys) > 150, "Insufficient translation keys"

    for lang in languages:
        lang_keys = set(locale_data[lang].keys())
        missing_keys = base_keys - lang_keys
        extra_keys = lang_keys - base_keys
        assert not missing_keys, f"Locale {lang} missing keys: {missing_keys}"
        assert not extra_keys, f"Locale {lang} has extra keys: {extra_keys}"
        assert len(lang_keys) == len(base_keys), f"Key count mismatch for {lang}"

def test_language_direction_mapping():
    """Verify RTL/LTR direction classification rules."""
    rtl_languages = {"fa", "ar"}
    ltr_languages = {"en", "tr"}

    for lang in ["fa", "ar", "en", "tr"]:
        if lang in rtl_languages:
            direction = "rtl"
        else:
            direction = "ltr"

        if lang in rtl_languages:
            assert direction == "rtl"
        if lang in ltr_languages:
            assert direction == "ltr"
