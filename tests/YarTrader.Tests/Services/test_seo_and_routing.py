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

def test_protected_trading_core_untouched():
    """Verify LIVE_TRADING_ENABLED remains hard-locked to False."""
    import os
    from unittest.mock import patch
    from src.Infrastructure.Configuration.settings import BaseSettings
    with patch.dict(os.environ, {"RG_DB_SECURE_TOKEN": "mock_test_token"}):
        cfg = BaseSettings()
        assert cfg.live_trading_enabled is False
    assert os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("false", "0")

def test_deploy_production_invokes_iis_remediation():
    """Verify deploy_production.ps1 resolves and invokes setup_iis_reverse_proxy.ps1 via $PSScriptRoot and fails closed on errors."""
    import os
    deploy_script_path = "scripts/deploy_production.ps1"
    assert os.path.exists(deploy_script_path)
    with open(deploy_script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule 1: Step 3.5 dedicated section is present
    step35_pos = content.find("STEP 3.5")
    assert step35_pos != -1
    step35_block = content[step35_pos:step35_pos + 1200]

    # Rule 2: Path resolved relative to $PSScriptRoot
    assert 'Join-Path $PSScriptRoot "setup_iis_reverse_proxy.ps1"' in step35_block or "setup_iis_reverse_proxy.ps1" in step35_block

    # Rule 3: Missing script causes deployment failure with Exit 1
    assert "Test-Path" in step35_block
    assert "Exit 1" in step35_block

    # Rule 4: Execution check & non-zero exit code / exception causes deployment failure with Exit 1
    assert "& $IISProxyScript" in step35_block
    assert "$LASTEXITCODE" in step35_block
    assert "catch" in step35_block

def test_iis_physical_path_environment_variable_expansion():
    """Verify IIS physicalPath environment variables are expanded before Test-Path."""
    import os

    script_path = "scripts/setup_iis_reverse_proxy.ps1"
    assert os.path.exists(script_path)

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    expand_pos = content.find(
        "[System.Environment]::ExpandEnvironmentVariables($SitePath)"
    )
    test_path_pos = content.find(
        "(Test-Path $SitePath)", expand_pos
    )

    assert expand_pos != -1, (
        "Missing ExpandEnvironmentVariables($SitePath)"
    )
    assert test_path_pos != -1, (
        "Test-Path $SitePath must exist after environment expansion"
    )
    assert expand_pos < test_path_pos, (
        "Environment variable expansion must occur before Test-Path"
    )

    staging_expand_pos = content.find(
        "[System.Environment]::ExpandEnvironmentVariables($StagingSitePath)"
    )
    staging_test_path_pos = content.find(
        "(Test-Path $StagingSitePath)", staging_expand_pos
    )

    assert staging_expand_pos != -1, (
        "Missing ExpandEnvironmentVariables($StagingSitePath)"
    )
    assert staging_test_path_pos != -1, (
        "Test-Path $StagingSitePath must exist after environment expansion"
    )
    assert staging_expand_pos < staging_test_path_pos, (
        "Staging environment variable expansion must occur before Test-Path"
    )

    assert "Exit 1" in content
    assert "127.0.0.1:3000" not in content

def test_content_security_policy_google_identity_and_font_support():
    """Verify IIS setup script emits CSP permitting Google Identity Services & Vazirmatn fonts without unrestricted wildcards or secret leaks."""
    import os
    script_path = "scripts/setup_iis_reverse_proxy.ps1"
    assert os.path.exists(script_path)
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Rule A: CSP permits Google Identity Services script, frame, connect, style, and img
    assert 'script-src \'self\' \'unsafe-inline\' \'unsafe-eval\' https://accounts.google.com/gsi/client' in content
    assert 'frame-src \'self\' https://accounts.google.com/' in content
    assert 'connect-src \'self\' ws: wss: https://accounts.google.com/gsi/' in content
    assert 'style-src \'self\' \'unsafe-inline\' https://accounts.google.com/gsi/style https://cdn.jsdelivr.net' in content
    assert 'font-src \'self\' data: https://cdn.jsdelivr.net' in content
    assert 'img-src \'self\' data: blob: https://*.googleusercontent.com https://*.gstatic.com' in content

    # Rule B: CSP is NOT unrestricted (no default-src * or script-src *)
    assert "default-src *" not in content
    assert "script-src *" not in content

    # Rule C: No Google Client Secret is in frontend source
    terminal_app = "trader-terminal/src/App.jsx"
    if os.path.exists(terminal_app):
        with open(terminal_app, "r", encoding="utf-8") as f:
            app_src = f.read()
            assert "client_secret" not in app_src.lower()
            assert "google_client_secret" not in app_src.lower()

    # Rule D: No YarOperator/M12 token is exposed in browser code
    trader_src_dir = "trader-terminal/src"
    if os.path.exists(trader_src_dir):
        for root, _, files in os.walk(trader_src_dir):
            for file in files:
                if file.endswith((".js", ".jsx", ".ts", ".tsx", ".html")):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_src = f.read()
                        assert "OPERATOR_OWNER_TOKEN" not in file_src
                        assert "OPERATOR_SERVER_SECRET" not in file_src
