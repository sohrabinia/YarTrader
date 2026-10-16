from pathlib import Path
import xml.etree.ElementTree as ET


def test_iis_config_serves_spa_and_keeps_runtime_controls_fail_closed():
    root = Path(__file__).resolve().parents[2]
    config = ET.parse(root / "deploy" / "iis" / "web.config").getroot()
    rules = config.find("./system.webServer/rewrite/rules")
    assert rules is not None
    names = [rule.get("name") for rule in list(rules)]
    assert names.index("Block Unwired Runtime Controls And Uninstrumented Telemetry") < names.index("Serve Existing Static Files")
    assert names.index("Serve YarTrader SPA Root") < names.index("Serve Existing Static Files")
    assert names.index("Serve Existing Static Files") < names.index("YarTrader SPA Route Fallback") < names.index("YarTrader Catch-All Route")

    block = next(rule for rule in list(rules) if rule.get("name") == "Block Unwired Runtime Controls And Uninstrumented Telemetry")
    pattern = block.find("match").get("url")
    for route in ("api/control", "api/mode", "api/risk/emergency_stop", "api/devops/status", "api/devops/metrics", "v1/runtime"):
        assert route in pattern
    assert block.find("action").get("statusCode") == "503"

    root_rule = next(rule for rule in list(rules) if rule.get("name") == "Serve YarTrader SPA Root")
    assert root_rule.find("match").get("url") == "^$"
    assert root_rule.find("action").get("url") == "index.html"
