import os
import json
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Infrastructure.version import get_application_version_info

client = TestClient(app)

def test_version_endpoints():
    """Verify that version endpoints return 200 OK with correct JSON schema."""
    for path in ["/api/version", "/api/system/version", "/v1/version"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["application"] == "YarTrader"
        assert "version" in data
        assert "commit" in data
        assert "environment" in data

def test_dynamic_homepage_version_interpolation(monkeypatch):
    """
    Version Acceptance Test (Sections 11 & 12):
    Prove that changing the authoritative version source (e.g. 7.0 -> 7.1)
    dynamically updates homepage welcome text across all 5 languages (FA, EN, TR, AR, DE)
    without modifying frontend component source code.
    """
    # Test A: Default version 7.0
    monkeypatch.setenv("APP_VERSION", "7.0")
    info_70 = get_application_version_info()
    assert info_70["version"] == "7.0"

    res = client.get("/api/version")
    assert res.status_code == 200
    assert res.json()["version"] == "7.0"

    # Verify interpolation across all 5 locales
    locales_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "trader-terminal", "public", "locales")

    expected_70 = {
        "fa": "به سامانه YarTrader v7.0 خوش آمدید",
        "en": "Welcome to YarTrader v7.0",
        "tr": "YarTrader v7.0'a Hoş Geldiniz",
        "ar": "مرحباً بكم في YarTrader v7.0"
    }

    for lang, expected_str in expected_70.items():
        filepath = os.path.join(locales_dir, f"{lang}.json")
        with open(filepath, "r", encoding="utf-8") as f:
            locale_data = json.load(f)
        template = locale_data["welcome_title"]
        rendered = template.replace("{{version}}", info_70["version"]).replace("{version}", info_70["version"])
        assert rendered == expected_str, f"Mismatch for locale {lang}"

    # Test B: Change authoritative version to 7.1 without changing component source
    monkeypatch.setenv("APP_VERSION", "7.1")
    info_71 = get_application_version_info()
    assert info_71["version"] == "7.1"

    res_71 = client.get("/api/version")
    assert res_71.status_code == 200
    assert res_71.json()["version"] == "7.1"

    expected_71 = {
        "fa": "به سامانه YarTrader v7.1 خوش آمدید",
        "en": "Welcome to YarTrader v7.1",
        "tr": "YarTrader v7.1'a Hoş Geldiniz",
        "ar": "مرحباً بكم في YarTrader v7.1"
    }

    for lang, expected_str in expected_71.items():
        filepath = os.path.join(locales_dir, f"{lang}.json")
        with open(filepath, "r", encoding="utf-8") as f:
            locale_data = json.load(f)
        template = locale_data["welcome_title"]
        rendered = template.replace("{{version}}", info_71["version"]).replace("{version}", info_71["version"])
        assert rendered == expected_str, f"Mismatch for locale {lang} on version 7.1"
