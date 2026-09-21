import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

client = TestClient(app)

def test_sitemap_xml_get_and_head():
    """Verify /sitemap.xml returns HTTP 200 with application/xml content type for GET and HEAD requests."""
    res_get = client.get("/sitemap.xml")
    assert res_get.status_code == 200
    assert "xml" in res_get.headers.get("content-type", "").lower()
    assert "<urlset" in res_get.text
    assert "https://yartrader.com/fa" in res_get.text
    assert "https://yartrader.com/de" not in res_get.text

    res_head = client.head("/sitemap.xml")
    assert res_head.status_code == 200
    assert "xml" in res_head.headers.get("content-type", "").lower()

def test_robots_txt_get_and_head():
    """Verify /robots.txt returns HTTP 200 text/plain referencing https://yartrader.com/sitemap.xml."""
    res_get = client.get("/robots.txt")
    assert res_get.status_code == 200
    assert "text/plain" in res_get.headers.get("content-type", "").lower()
    assert "Sitemap: https://yartrader.com/sitemap.xml" in res_get.text
    assert "Disallow: /admin" in res_get.text
    assert "Disallow: /dashboard" in res_get.text

    res_head = client.head("/robots.txt")
    assert res_head.status_code == 200
    assert "text/plain" in res_head.headers.get("content-type", "").lower()

def test_four_localized_spa_routes():
    """Verify localized SPA roots and subroutes return HTTP 200 for GET and HEAD methods across exact 4 languages (fa, en, tr, ar)."""
    languages = ["fa", "en", "tr", "ar"]
    subroutes = ["", "/admin", "/blog", "/news", "/faq", "/guide", "/pricing", "/contact", "/support", "/login", "/register", "/dashboard"]

    for lang in languages:
        for sub in subroutes:
            url = f"/{lang}{sub}"
            res_get = client.get(url)
            assert res_get.status_code == 200, f"Failed GET for {url}"
            assert "text/html" in res_get.headers.get("content-type", "").lower()

            res_head = client.head(url)
            assert res_head.status_code == 200, f"Failed HEAD for {url}"

def test_operator_route_served_by_yartrader_spa():
    """Verify /Operator and /operator are served directly by YarTrader SPA (returns index.html, not YarOperator proxy)."""
    res_upper = client.get("/Operator")
    assert res_upper.status_code == 200
    assert "text/html" in res_upper.headers.get("content-type", "").lower()
    assert "YarTrader" in res_upper.text
    assert "YarOperator — Executive Assistant" not in res_upper.text

    res_lower = client.get("/operator")
    assert res_lower.status_code == 200
    assert "text/html" in res_lower.headers.get("content-type", "").lower()
    assert "YarTrader" in res_lower.text

def test_no_browser_facing_v1_operator_routes():
    """Verify YarTrader FastAPI does not expose raw browser-facing /api/v1/operator routes."""
    res = client.get("/api/v1/operator/chat")
    assert res.status_code == 404

def test_de_locale_removed():
    """Verify German (/de) public route is removed or disallowed as active public SEO locale."""
    res = client.get("/de")
    assert res.status_code == 404

def test_api_404_isolation():
    """Verify that unknown /api/* endpoints return real HTTP 404 JSON instead of HTML SPA fallbacks."""
    res = client.get("/api/nonexistent-endpoint-xyz-123")
    assert res.status_code == 404
    assert res.headers.get("content-type") == "application/json"
    assert res.json() == {"detail": "Not Found"}

def test_iis_powershell_script_template_rules():
    """Verify setup_iis_reverse_proxy.ps1 contains no rewrite rules targeting port 3000 and resolves physicalPath before writing."""
    import os
    script_path = "scripts/setup_iis_reverse_proxy.ps1"
    assert os.path.exists(script_path)
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule 1: No rewrite target to 3000 in rewrite actions or URLs
    assert "url=\"http://127.0.0.1:3000" not in content
    assert "url=\"${BackendUrl}/{R:1}\"" in content or "url=\"http://127.0.0.1:8000" in content

    # Rule 2: PhysicalPath resolution occurs BEFORE Web.config generation/writing
    step1_pos = content.find("STEP 1: RESOLVE IIS SITE PHYSICAL PATH")
    step2_pos = content.find("STEP 2: GENERATE RE-MEDIATED WEB.CONFIG")
    assert step1_pos != -1 and step2_pos != -1
    assert step1_pos < step2_pos

    # Rule 3: Conditional HTTPS handling based on $HasHttpsBinding
    assert "$HasHttpsBinding" in content
    assert "Redirect HTTP to HTTPS" in content

    # Rule 4: Fail-closed exception handling (Exit 1 on inspection catch block, no fallback assignment)
    catch_pos = content.find("catch {")
    assert catch_pos != -1
    catch_block = content[catch_pos:catch_pos+350]
    assert "Exit 1" in catch_block
    assert "$ResolvedProductionPath = $DefaultProductionPath" not in catch_block

    # Rule 5: Fail-closed non-admin/missing module path & staging write failure
    else_pos = content.find("WebAdministration module is missing")
    assert else_pos != -1
    else_block = content[else_pos:else_pos+300]
    assert "Exit 1" in else_block
    assert "Refusing to fall back" in else_block

    staging_catch_pos = content.find("Unable to write staging IIS web.config file!")
    assert staging_catch_pos != -1
    staging_catch_block = content[staging_catch_pos:staging_catch_pos+200]
    assert "Exit 1" in staging_catch_block

def test_deploy_production_invokes_iis_reverse_proxy_script():
    """Verify deploy_production.ps1 invokes setup_iis_reverse_proxy.ps1 before completion and propagates failure fail-closed."""
    import os
    deploy_script_path = "scripts/deploy_production.ps1"
    assert os.path.exists(deploy_script_path)
    with open(deploy_script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule A: deploy_production.ps1 defines $IISProxyScript referencing setup_iis_reverse_proxy.ps1
    assert "setup_iis_reverse_proxy.ps1" in content
    assert "$IISProxyScript" in content

    # Rule B: Invocation occurs before DEPLOYMENT PREPARATION COMPLETE
    step_pos = content.find("STEP 3.5: IIS Reverse Proxy & web.config Remediation")
    completion_pos = content.find("DEPLOYMENT PREPARATION COMPLETE!")
    assert step_pos != -1 and completion_pos != -1
    assert step_pos < completion_pos

    # Rule C & D: Failure propagation - $LASTEXITCODE -ne 0 triggers Exit 1
    step_block = content[step_pos:step_pos+600]
    assert "$LASTEXITCODE -ne 0" in step_block
    assert "Exit 1" in step_block

    # Rule E & F: setup_iis_reverse_proxy.ps1 is invoked directly without hardcoding web.config paths in deploy_production.ps1
    assert "web.config" not in content or "web.config Remediation" in content
    assert "C:\\inetpub\\wwwroot\\web.config" not in content

def test_protected_trading_core_untouched():
    """Verify LIVE_TRADING_ENABLED remains hard-locked to False."""
    import os
    from unittest.mock import patch
    from src.Infrastructure.Configuration.settings import BaseSettings
    with patch.dict(os.environ, {"RG_DB_SECURE_TOKEN": "mock_test_token"}):
        cfg = BaseSettings()
        assert cfg.live_trading_enabled is False
    assert os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("false", "0")
