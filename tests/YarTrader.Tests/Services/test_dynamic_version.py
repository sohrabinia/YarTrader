import os
import json
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Infrastructure.version import get_application_version_info, get_current_version_string

client = TestClient(app)

def test_version_endpoints():
    """Verify that version endpoints return 200 OK with complete release identity metadata."""
    for path in ["/api/version", "/api/system/version", "/v1/version"]:
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["application"] == "YarTrader"
        assert "version" in data
        assert "commit" in data
        assert "environment" in data
        assert "release_id" in data
        assert "build_id" in data
        assert "artifact_id" in data
        assert data["release_id"].startswith("rel-")
        assert data["build_id"].startswith("bld-")
        assert data["artifact_id"].startswith("art-yartrader-")

def test_release_identity_structure():
    """Verify that get_application_version_info returns deterministic release identity fields."""
    info = get_application_version_info()
    assert isinstance(info, dict)
    assert info["application"] == "YarTrader"
    assert "version" in info
    assert "commit" in info
    assert "release_id" in info
    assert "build_id" in info
    assert "artifact_id" in info
    short_sha = info["commit"][:12] if info["commit"] and info["commit"] != "UNKNOWN_COMMIT" else "000000000000"
    assert info["release_id"] == f"rel-{info['version']}-{short_sha}"
    assert info["artifact_id"] == f"art-yartrader-{info['version']}-{short_sha}"
    assert get_current_version_string() == str(info["version"])

def test_environment_override_behavior(monkeypatch):
    """Verify that environment variables (APP_VERSION, GIT_COMMIT) override defaults safely."""
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("GIT_COMMIT", "1234567890abcdef1234567890abcdef12345678")

    info = get_application_version_info()
    assert info["version"] == "9.9.9"
    assert info["commit"] == "1234567890abcdef1234567890abcdef12345678"
    assert info["release_id"] == "rel-9.9.9-1234567890ab"
    assert info["artifact_id"] == "art-yartrader-9.9.9-1234567890ab"

def test_protection_against_stale_commit_defaults(monkeypatch):
    """Verify that version.py does NOT fall back to stale hardcoded commit SHAs when unconfigured."""
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("YARTRADER_BUILD_SHA", raising=False)

    info = get_application_version_info()
    # Must NOT equal stale hardcoded historical SHA bdc6479406d83b01441839851ea034ad4c946ac5
    assert info["commit"] != "bdc6479406d83b01441839851ea034ad4c946ac5"

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
